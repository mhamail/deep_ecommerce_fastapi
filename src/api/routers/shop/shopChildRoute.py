from fastapi import APIRouter, Depends
from sqlmodel import select
from starlette.datastructures import UploadFile
from src.api.models.shop_model.shopModel import Shop
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requirePermission,
    requireAdmin,
    verifiedUser,
)
from src.api.models.shop_model.ShopChildModel import (
    ShopUser,
    ShopUserRead,
    ShopUserCreate,
    ShopUserUpdate,
)
from src.api.models.userModel import User

router = APIRouter(prefix="/shop-users", tags=["Shop Users"])


@router.post("/create", response_model=ShopUserRead)
async def create_ride(
    session: GetSession,
    request: ShopUserCreate = Depends(),
    user=requirePermission(["shop_admin"]),
):

    user_id = session.exec(select(User).where(User.email == request.email)).first()
    request.shop_id = user.get("shop").get("id")

    # ✅ Create shop User
    shopUser = ShopUser(**request.model_dump())

    session.add(shopUser)
    session.commit()
    session.refresh(shopUser)

    return api_response(
        201,
        "Shop Updated Successfully",
        ShopUserRead.model_validate(shopUser),
    )
