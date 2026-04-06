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
    verifiedUser,
)
from src.api.models.shop_model.shopModel import (
    Shop,
    ShopForm,
    ShopRead,
    ShopReadWithOwner,
)
from src.api.core.operation.media import (
    deleteMediaFiles,
    uploadMediaFiles,
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

    request.slug = uniqueSlugify(session, Shop, request.name)

    request.owner_id = user_id

    data = serialize_obj(request)
    await uploadMediaFiles(session, data, request)

    # ✅ Create shop
    shop = Shop(**data)

    session.add(shop)
    session.commit()
    session.refresh(shop)

    return api_response(
        201,
        "Shop Updated Successfully",
        ShopRead.model_validate(shop),
    )


@router.put("/update", response_model=ShopRead)
async def update_ride(
    user: verifiedUser,
    session: GetSession,
    request: ShopForm = Depends(),
):
    user_id = user.get("id")
    read = session.exec(select(Shop).where(Shop.owner_id == user_id)).first()

    raiseExceptions((read, 404, "Shop not found"))
    if request.name:
        request.slug = uniqueSlugify(session, Shop, request.name)

    if isinstance(request.cover_image, UploadFile):
        await deleteMediaFiles(session, read.cover_image)
        request.cover_image = await uploadSingleMedia(request.cover_image, session)

    if isinstance(request.logo, UploadFile):
        await deleteMediaFiles(session, read.logo)
        request.logo = await uploadSingleMedia(request.logo, session)

    # ✅ update shop
    update_data = updateOp(read, request, session)

    session.commit()
    session.refresh(update_data)

    return api_response(
        201,
        "Shop Created Successfully",
        ShopRead.model_validate(update_data),
    )


@router.get("/read", response_model=ShopRead)
def findOne(
    session: GetSession,
    user: verifiedUser,
):

    user_id = user.get("id")
    statement = select(Shop).where(Shop.owner_id == user_id)
    read = session.exec(statement).first()  # Like findById

    raiseExceptions((read, 404, "Shop not found"))
    data = ShopRead.model_validate(read)

    return api_response(200, "Shop Found", data)


@router.get("/read/{id}", response_model=ShopReadWithOwner)
def findOne(
    id: int,
    session: GetSession,
):

    read = session.get(Shop, id)  # Like findById

    raiseExceptions((read, 404, "Shop not found"))
    data = ShopReadWithOwner.model_validate(read)

    if not data.owner or not data.owner.verified:
        return api_response(400, "User Not Verified")

    return api_response(200, "Shop Found", data)


@router.delete("/delete/{id}", response_model=dict)
async def delete_role(
    id: int,
    session: GetSession,
    user=requirePermission("shop_delete"),
):
    shop = session.get(Shop, id)

    raiseExceptions((shop, 404, "Shop Data not found"))

    await deleteMediaFiles(session, shop.cover_image, shop.logo)

    session.delete(shop)
    session.commit()
    return api_response(200, f"Shop {shop.name} deleted")


@router.get("/list", response_model=list[ShopReadWithOwner])
def list(
    query_params: ListQueryParams,
    user=requirePermission("shop_list"),
):
    query_params = vars(query_params)
    searchFields = ["name", "slug", "description"]

    return listRecords(
        query_params=query_params,
        searchFields=searchFields,
        Model=Shop,
        Schema=ShopReadWithOwner,
    )
