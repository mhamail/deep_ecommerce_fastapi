from fastapi import APIRouter, Depends
from sqlmodel import select
from starlette.datastructures import UploadFile
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, serialize_obj
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
    requireAdmin,
    verifiedUser,
)
from src.api.models.shopModel import (
    Shop,
    ShopForm,
    ShopRead,
)
from src.api.core.operation.media import (
    delete_media_items,
    entryMedia,
    uploadImage,
    uploadSingleMedia,
)

router = APIRouter(prefix="/shop", tags=["Shop"])


@router.post("/create", response_model=ShopRead)
async def create_ride(
    user: verifiedUser,
    session: GetSession,
    request: ShopForm = Depends(),
):
    user_id = user.get("id")

    request.slug = uniqueSlugify(session, Shop, "string")

    request.owner_id = user_id

    data = serialize_obj(request)
    data["cover_image"] = await uploadSingleMedia(request.cover_image, session)

    data["logo"] = await uploadSingleMedia(request.logo, session)

    # ✅ Create shop
    shop = Shop(**data)

    session.add(shop)
    session.commit()
    session.refresh(shop)

    return api_response(
        201,
        "Shop Created Successfully",
        ShopRead.model_validate(shop),
    )
