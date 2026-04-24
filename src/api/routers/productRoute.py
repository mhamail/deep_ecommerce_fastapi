from fastapi import APIRouter, Depends
from sqlmodel import select
from starlette.datastructures import UploadFile
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
    requireAdmin,
    requireShopPermission,
    verifiedUser,
)
from src.api.models.productModel import (
    Product,
    ProductForm,
    ProductRead,
)

from src.api.core.operation.media import (
    deleteMediaFiles,
    uploadMediaFiles,
    uploadSingleMedia,
)

router = APIRouter(prefix="/product", tags=["Product"])


@router.post("/create", response_model=ProductRead)
async def create_product(
    session: GetSession,
    request: ProductForm = Depends(),
    user=requireShopPermission(["product:create"]),
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
