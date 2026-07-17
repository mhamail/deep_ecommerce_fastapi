from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import exists, select
from src.api.models.product_model.ProductVariantModel import ProductVariant
from src.api.routers.category.fn import get_category_subtree_ids
from src.api.models.category_model import Category
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireShopPermission,
)
from src.api.models.product_model.productModel import (
    Product,
    ProductForm,
    ProductRead,
    ProductSingleRead,
)

from src.api.core.operation.media import (
    arrangeUpdateMultiMedia,
    arrangeUpdateMultiMedia,
    deleteMediaFiles,
    uploadMediaFiles,
    uploadSingleMedia,
)

router = APIRouter(prefix="/product", tags=["Product"])


def _variant_payload(product_id: int, variant: dict):
    return {
        "product_id": product_id,
        "price": variant.get("price"),
        "discount_price": variant.get("discount_price"),
        "stock": variant.get("stock", 0),
        "is_in_stock": variant.get("is_in_stock", True),
        "sku": variant.get("sku"),
        "attributes": variant.get("attributes", {}),
        "image": variant.get("image"),
    }


def _default_variant_payload(product: Product):
    return {
        "product_id": product.id,
        "price": product.price,
        "discount_price": product.discount_price,
        "stock": product.stock,
        "is_in_stock": product.is_in_stock,
        "sku": product.sku,
        "attributes": {},
        "image": product.thumbnail,
    }


def _update_variant_from_payload(product_variant: ProductVariant, payload: dict):
    for field, value in payload.items():
        if field in {"id", "product_id"}:
            continue

        if value is not None and hasattr(product_variant, field):
            setattr(product_variant, field, value)


def upsert_product_variants(session, product: Product, request: ProductForm):
    if not request.variant_data:
        return

    for variant in request.variant_data:
        variant_id = variant.get("id")

        if variant_id:
            product_variant = session.exec(
                select(ProductVariant).where(
                    ProductVariant.id == variant_id,
                    ProductVariant.product_id == product.id,
                )
            ).first()
            raiseExceptions((product_variant, 404, "Product Variant not found"))

            _update_variant_from_payload(product_variant, variant)
            session.add(product_variant)
            continue

        # =====================================
        # CREATE NEW VARIANT
        # =====================================

        else:

            product_variant = ProductVariant(
                **_variant_payload(
                    product.id,
                    variant,
                )
            )

            session.add(product_variant)


@router.post("/create", response_model=ProductSingleRead)
async def create_product(
    session: GetSession,
    user=requireShopPermission(["product:create"]),
    request: ProductForm = Depends(),
):

    user_id = user.get("id")
    shop_id = user.get("default_shop_id")

    # ==========================
    # Validate category (must be leaf)
    # ==========================
    if request.category_id:
        has_children = session.exec(
            select(exists().where(Category.parent_id == request.category_id))
        ).one()

        if has_children:
            return api_response(
                400,
                "Please select a sub-category (last level). Parent categories are not allowed.",
            )

    # ==========================
    # Prepare data
    # ==========================
    request.slug = uniqueSlugify(session, Product, request.name)
    request.created_by = user_id
    request.shop_id = shop_id

    data = serialize_obj(request)

    await uploadMediaFiles(session, data, request)

    # ==========================
    # Create product
    # ==========================

    product = Product(**data)

    session.add(product)
    session.flush()

    if request.variant_data and len(request.variant_data) > 0:
        for variant in request.variant_data:

            image = variant.get("image")

            if image and not isinstance(image, str):
                image = await uploadSingleMedia(image, session)

            variant_data = {
                "product_id": product.id,
                "price": variant.get("price"),
                "discount_price": variant.get("discount_price"),
                "stock": variant.get("stock", 0),
                "is_in_stock": variant.get("is_in_stock", True),
                "sku": variant.get("sku"),
                "attributes": variant.get("attributes", {}),
                # "image": image,
            }

            productVariant = ProductVariant(**variant_data)
            session.add(productVariant)
    else:
        variant_data = _default_variant_payload(product)
        # =============================
        # Add Default product Variant
        # =============================
        productVariant = ProductVariant(**variant_data)

        session.add(productVariant)

    session.commit()
    session.refresh(product)

    return api_response(
        201,
        "Product Created Successfully",
        ProductSingleRead.model_validate(product),
    )


@router.post("/update/{id}", response_model=ProductSingleRead)
async def update_product(
    id: int,
    session: GetSession,
    user=requireShopPermission(["product:create", "product:update"]),
    request: ProductForm = Depends(),
):
    shop_id = user.get("default_shop_id")
    product = session.exec(
        select(Product).where(Product.id == id, Product.shop_id == shop_id)
    ).first()
    raiseExceptions((product, 404, "Product not found"))
    if request.name:
        request.slug = uniqueSlugify(session, Product, request.name)

    if isinstance(request.thumbnail, UploadFile):
        await deleteMediaFiles(session, product.thumbnail)
        request.thumbnail = await uploadSingleMedia(request.thumbnail, session)

    images = getattr(request, "images", None)
    if images:
        print("Uploading new images...", images)

        request.images = await arrangeUpdateMultiMedia(
            session, product.images, request.images, request.delete_images
        )

    # ==========================
    # UPDATE
    # ==========================

    updated_product = updateOp(product, request, session)
    upsert_product_variants(session, updated_product, request)

    session.commit()
    session.refresh(updated_product)

    return api_response(
        200,
        "Product Updated Successfully",
        ProductSingleRead.model_validate(updated_product),
    )


@router.get("/read/{id}", response_model=ProductSingleRead)
def findOne(
    id: int,
    session: GetSession,
):

    read = session.get(
        Product,
        id,
        options=[
            joinedload(Product.shop),
            joinedload(Product.category),
            selectinload(Product.variants),
        ],
    )

    raiseExceptions((read, 404, "Product not found"))
    data = ProductSingleRead.model_validate(read)

    return api_response(200, "Product Found", data)


PRODUCT_LIST_JOIN_OPTIONS = [
    selectinload(Product.shop),
    selectinload(Product.category),
    selectinload(Product.variants),
]


@router.get("/list", response_model=list[ProductRead])
def list(
    query_params: ListQueryParams,
):
    query_params = vars(query_params)
    searchFields = ["name", "description", "slug", "sku"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        join_options=PRODUCT_LIST_JOIN_OPTIONS,
    )


@router.get("/related-category/{category_id}")
def list(query_params: ListQueryParams, category_id: int, session: GetSession):
    query_params = vars(query_params)
    searchFields = ["name", "description", "slug", "sku"]

    category_ids = get_category_subtree_ids(session, category_id)

    def otherFilters(statement, Model):
        return statement.where(Model.category_id.in_(category_ids))

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        otherFilters=otherFilters,
        join_options=PRODUCT_LIST_JOIN_OPTIONS,
    )


@router.get("/my-products")
def list(
    query_params: ListQueryParams,
    user=requireShopPermission(["product:create", "product:read"]),
):
    shop_id = user.get("default_shop_id")
    query_params = vars(query_params)
    searchFields = ["name", "description", "slug", "sku"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        customFilters=[["shop_id", shop_id]],
        join_options=PRODUCT_LIST_JOIN_OPTIONS,
    )
