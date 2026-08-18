import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from starlette.datastructures import UploadFile as FormUploadFile
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import delete, exists, select
from src.api.models.cart_model.cartItemModel import CartItem
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
        "position": variant.get("position", 0),
    }


def _remove_variants_from_carts(session, variant_ids):
    """Deleting a variant that's still sitting in someone's cart violates the
    cart_items -> product_variants foreign key, so drop those cart rows first."""
    if not variant_ids:
        return
    session.exec(delete(CartItem).where(CartItem.product_variant_id.in_(variant_ids)))


def _update_variant_from_payload(product_variant: ProductVariant, payload: dict):
    for field, value in payload.items():
        if field in {"id", "product_id"}:
            continue

        if value is not None and hasattr(product_variant, field):
            setattr(product_variant, field, value)


def _extract_variant_images(form_data) -> dict:
    """Per-variant image files travel as `variant_image_{index}` multipart
    fields — variant_data itself is a JSON string blob, so files can't live
    inside it, and the variant count isn't known ahead of time (can't
    pre-declare N fields on ProductForm)."""
    images = {}
    for key, value in form_data.multi_items():
        if key.startswith("variant_image_") and isinstance(value, FormUploadFile):
            try:
                index = int(key.removeprefix("variant_image_"))
            except ValueError:
                continue
            images[index] = value
    return images


async def upsert_product_variants(
    session, product: Product, request: ProductForm, variant_images: dict
):
    variant_data = request.variant_data or []
    # Snapshot BEFORE creating/updating anything this call — newly created
    # variants never carry a client-supplied id, so diffing against
    # `product.variants` read *after* the loop below would wrongly treat
    # them as "existing but missing from the payload" and delete them.
    existing_ids_before = {v.id for v in product.variants}

    for index, variant in enumerate(variant_data):
        variant["position"] = index
        variant_id = variant.get("id")
        image_file = variant_images.get(index)

        if variant_id:
            product_variant = session.exec(
                select(ProductVariant).where(
                    ProductVariant.id == variant_id,
                    ProductVariant.product_id == product.id,
                )
            ).first()
            raiseExceptions((product_variant, 404, "Product Variant not found"))

            if image_file:
                if product_variant.image:
                    await deleteMediaFiles(session, product_variant.image)
                variant["image"] = await uploadSingleMedia(
                    image_file, session, shop_id=product.shop_id
                )

            _update_variant_from_payload(product_variant, variant)
            session.add(product_variant)
            continue

        # =====================================
        # CREATE NEW VARIANT
        # =====================================

        else:
            if image_file:
                variant["image"] = await uploadSingleMedia(
                    image_file, session, shop_id=product.shop_id
                )

            product_variant = ProductVariant(
                **_variant_payload(
                    product.id,
                    variant,
                )
            )

            session.add(product_variant)

    # =====================================
    # DELETE VARIANTS DROPPED FROM THE LIST
    # =====================================
    incoming_ids = {v.get("id") for v in variant_data if v.get("id")}
    dropped_ids = existing_ids_before - incoming_ids
    _remove_variants_from_carts(session, dropped_ids)
    for missing_id in dropped_ids:
        existing_variant = session.get(ProductVariant, missing_id)
        if existing_variant:
            if existing_variant.image:
                await deleteMediaFiles(session, existing_variant.image)
            session.delete(existing_variant)


@router.post("/create", response_model=ProductSingleRead)
async def create_product(
    session: GetSession,
    http_request: Request,
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

    await uploadMediaFiles(session, data, request, shop_id=shop_id)

    # ==========================
    # Create product
    # ==========================

    product = Product(**data)

    session.add(product)
    session.flush()

    variant_images = _extract_variant_images(await http_request.form())
    print(variant_images)
    await upsert_product_variants(session, product, request, variant_images)

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
    http_request: Request,
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

    if isinstance(request.thumbnail, FormUploadFile):
        if product.thumbnail:
            await deleteMediaFiles(session, product.thumbnail)
        request.thumbnail = await uploadSingleMedia(
            request.thumbnail, session, shop_id=shop_id
        )

    # Run even when there are no new files, as long as something is being
    # removed — a delete-only edit (no new upload) must still persist.
    if request.images or request.delete_images:
        request.images = await arrangeUpdateMultiMedia(
            session,
            product.images,
            request.images,
            request.delete_images,
            shop_id=shop_id,
        )
    else:
        # Neither add nor remove anything — leave the stored list untouched
        # (updateOp below would otherwise overwrite it with the empty [] the
        # form always carries when no images/delete_images were sent).
        del request.images

    # ==========================
    # UPDATE
    # ==========================

    updated_product = updateOp(product, request, session)

    variant_images = _extract_variant_images(await http_request.form())
    await upsert_product_variants(session, updated_product, request, variant_images)

    session.commit()
    session.refresh(updated_product)

    return api_response(
        200,
        "Product Updated Successfully",
        ProductSingleRead.model_validate(updated_product),
    )


@router.delete("/delete/{id}")
async def delete_product(
    id: int,
    session: GetSession,
    user=requireShopPermission(["product:delete"]),
):
    shop_id = user.get("default_shop_id")
    product = session.exec(
        select(Product)
        .options(selectinload(Product.variants))
        .where(Product.id == id, Product.shop_id == shop_id)
    ).first()
    raiseExceptions((product, 404, "Product not found"))

    # Deleting a variant that's still in someone's cart violates the FK, so
    # drop those cart rows first.
    _remove_variants_from_carts(session, [v.id for v in product.variants])

    # Delete every variant (and its image) that belongs to this product
    for variant in product.variants:
        if variant.image:
            await deleteMediaFiles(session, variant.image)
        session.delete(variant)

    # Delete the product's own media, then the product itself
    await deleteMediaFiles(session, product.thumbnail, product.images)
    session.delete(product)
    session.commit()

    return api_response(200, "Product deleted successfully")


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


def _extract_price_sort(query_params: dict):
    """Product has no real 'price' column — it lives on ProductVariant, and
    Product.min_price/max_price are Python-only @property values, not SQL
    columns. `listRecords` reads `sort` out of query_params before
    `otherFilters` ever runs, so the generic sort handler would already be
    committed to `getattr(Product, "price")` (raising "Invalid sort
    parameter: price") by the time otherFilters could react. So: pull a
    price-family sort out of query_params here (route level, before
    listRecords sees it) and return enough info to build the correct
    correlated-subquery ordering via otherFilters instead."""
    sort_raw = query_params.get("sort")
    if not sort_raw:
        return None

    try:
        column_name, direction = json.loads(sort_raw)
    except Exception:
        return None

    if column_name not in ("price", "min_price", "max_price"):
        return None

    query_params["sort"] = None  # stop the generic sort handler from also trying
    return column_name, (direction or "asc").lower()


def _price_order_by(column_name: str, direction: str):
    # Effective price per variant = discount_price if set, else price —
    # same semantics as Product.min_price/max_price.
    effective_price = func.coalesce(ProductVariant.discount_price, ProductVariant.price)
    agg_fn = func.max if column_name == "max_price" else func.min
    price_subq = (
        select(agg_fn(effective_price))
        .where(ProductVariant.product_id == Product.id)
        .correlate(Product)
        .scalar_subquery()
    )
    return price_subq.desc() if direction == "desc" else price_subq.asc()


PRODUCT_LIST_JOIN_OPTIONS = [
    selectinload(Product.shop),
    selectinload(Product.category),
    selectinload(Product.variants),
]

# Product-facing search fields — "sku" lives on ProductVariant, not Product,
# so it must be searched via the dotted relation path (resolve_column joins
# it automatically); a bare "sku" here raises AttributeError the moment
# anyone actually searches.
PRODUCT_SEARCH_FIELDS = ["name", "description", "slug", "variants.sku"]


@router.get("/list", response_model=list[ProductRead])
def list(
    query_params: ListQueryParams,
):
    query_params = vars(query_params)
    price_sort = _extract_price_sort(query_params)

    def otherFilters(statement, Model):
        if price_sort:
            statement = statement.order_by(_price_order_by(*price_sort))
        return statement

    return listRecords(
        query_params=query_params,
        searchFields=PRODUCT_SEARCH_FIELDS,
        Model=Product,
        Schema=ProductRead,
        otherFilters=otherFilters,
        join_options=PRODUCT_LIST_JOIN_OPTIONS,
    )


@router.get("/related-category/{category_id}")
def list(
    query_params: ListQueryParams,
    category_id: int,
    session: GetSession,
):
    query_params = vars(query_params)
    price_sort = _extract_price_sort(query_params)

    category_ids = get_category_subtree_ids(session, category_id)

    def otherFilters(statement, Model):
        statement = statement.where(Model.category_id.in_(category_ids))
        if price_sort:
            statement = statement.order_by(_price_order_by(*price_sort))
        return statement

    return listRecords(
        query_params=query_params,
        searchFields=PRODUCT_SEARCH_FIELDS,
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
    price_sort = _extract_price_sort(query_params)
    searchFields = PRODUCT_SEARCH_FIELDS

    def otherFilters(statement, Model):
        if price_sort:
            statement = statement.order_by(_price_order_by(*price_sort))
        return statement

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Product,
        Schema=ProductRead,
        customFilters=[["shop_id", shop_id]],
        otherFilters=otherFilters,
        join_options=PRODUCT_LIST_JOIN_OPTIONS,
    )
