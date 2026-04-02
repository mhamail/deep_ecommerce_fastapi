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
    ShopReadWithOwner,
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


# @router.delete("/delete/{id}", response_model=dict)
# def delete_role(
#     id: int,
#     session: GetSession,
#     user=requirePermission("shop_delete"),
# ):
#     user_id = user.get("id")

#     shop = session.get(Shop, id)

#     raiseExceptions((shop, 404, "Shop Data not found"))
#     if ride.user_id != user_id:
#         return api_response(403, "You are not allowed to update this ride")

#     filenames_to_delete = []
#     # -------------------------
#     # CAR PIC
#     # -------------------------
#     if ride.car_pic and isinstance(ride.car_pic, dict):
#         filename = ride.car_pic.get("filename")
#         if filename:
#             filenames_to_delete.append(filename)

#     # -------------------------
#     # OTHER IMAGES
#     # -------------------------
#     if isinstance(ride.other_images, List) and ride.other_images:
#         for img in ride.other_images:
#             if isinstance(img, dict) and img.get("filename"):
#                 filenames_to_delete.append(img["filename"])

#     # -------------------------
#     # DELETE MEDIA FILES
#     # -------------------------
#     if filenames_to_delete:
#         delete_media_items(session, filenames=filenames_to_delete)

#     session.delete(ride)
#     session.commit()
#     return api_response(200, f"Ride {ride.id} deleted")


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
