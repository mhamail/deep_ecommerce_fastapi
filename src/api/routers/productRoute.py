from fastapi import APIRouter, Depends, UploadFile
from sqlmodel import select
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireShopPermission,
)
from src.api.models.productModel import (
    Product,
    ProductForm,
    ProductRead,
)

from src.api.core.operation.media import (
    arrangeUpdateMultiMedia,
    arrangeUpdateMultiMedia,
    deleteMediaFiles,
    uploadMediaFiles,
    uploadSingleMedia,
)

router = APIRouter(prefix="/product", tags=["Product"])


@router.post("/create", response_model=ProductRead)
async def create_product(
    session: GetSession,
    user=requireShopPermission(["product:create"]),
    request: ProductForm = Depends(),
):

    user_id = user.get("id")
    shop_id = user.get("default_shop_id")

    request.slug = uniqueSlugify(session, Product, request.name)

    request.created_by = user_id
    request.shop_id = shop_id

    data = serialize_obj(request)
    await uploadMediaFiles(session, data, request)

    # ✅ Create product
    product = Product(**data)

    session.add(product)
    session.commit()
    session.refresh(product)

    return api_response(
        201,
        "Product Created Successfully",
        ProductRead.model_validate(product),
    )


@router.post("/update/{id}", response_model=ProductRead)
async def update_product(
    id: int,
    session: GetSession,
    user=requireShopPermission(["product:create", "product:update"]),
    request: ProductForm = Depends(),
):

    user_id = user.get("id")
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

    session.commit()
    session.refresh(updated_product)

    return api_response(
        200,
        "Product Updated Successfully",
        ProductRead.model_validate(updated_product),
    )


@router.get("/read/{id}", response_model=ProductRead)
def findOne(
    id: int,
    session: GetSession,
):

    read = session.get(Product, id)

    raiseExceptions((read, 404, "Product not found"))
    data = ProductRead.model_validate(read)

    return api_response(200, "Product Found", data)


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
    )
