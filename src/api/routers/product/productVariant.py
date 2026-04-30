from fastapi import APIRouter, Depends, UploadFile
from sqlmodel import exists, select
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
from src.api.models.product_model.ProductVariant import (
    ProductVariant,
    ProductVariantRead,
    ProductVariantForm,
)
from src.api.models.product_model.productModel import Product


from src.api.core.operation.media import (
    arrangeUpdateMultiMedia,
    arrangeUpdateMultiMedia,
    deleteMediaFiles,
    uploadMediaFiles,
    uploadSingleMedia,
)

router = APIRouter(prefix="/product-variant", tags=["Product Variant"])


@router.post("/create/{product_id}", response_model=ProductVariantRead)
async def create_product(
    session: GetSession,
    product_id: int,
    user=requireShopPermission(["product:create"]),
    request: ProductVariantForm = Depends(),
):
    product = session.get(Product, product_id)
    raiseExceptions((product, 404, "Product not found"))

    # ==========================
    # Prepare data
    # ==========================
    request.product_id = product_id

    data = serialize_obj(request)

    await uploadMediaFiles(session, data, request)

    # ==========================
    # Add product Variant
    # ==========================
    productVariant = ProductVariant(**data)

    session.add(productVariant)
    session.commit()
    session.refresh(productVariant)

    return api_response(
        201,
        "Product Variant Add Successfully",
        ProductVariantRead.model_validate(productVariant),
    )
