from typing import Optional
from fastapi import APIRouter, Depends, Query
from starlette.datastructures import UploadFile as StarletteUploadFile

from src.api.core.operation.media import delete_media_items, entryMedia, uploadImage
from src.api.core.security import create_access_token, hash_password
from src.api.core.smtp import send_email
from src.api.routers.authRoute import exist_verified_email
from src.config import DOMAIN
from src.api.core import updateOp, requireSignin
from src.api.core.dependencies import GetSession, requireAdmin
from src.api.core.response import api_response, raiseExceptions

from src.api.models.userModel import (
    User,
    UserRead,
    UserUpdateForm,
)


router = APIRouter(prefix="/user", tags=["user"])


@router.get("/read", response_model=UserRead)
def get_user(
    user: requireSignin,
    session: GetSession,
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 400, "User not found"))
    user_read = UserRead.model_validate(db_user)
    return api_response(200, "User Found", user_read)


@router.get("/read/{id}", response_model=UserRead)
def get_user(
    id: int,
    session: GetSession,
):
    user_id = id
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 400, "User not found"))
    user_read = UserRead.model_validate(db_user)
    return api_response(200, "User Found", user_read)


@router.put("/update", response_model=UserRead)
async def update_user(
    user: requireSignin,
    session: GetSession,
    request: UserUpdateForm = Depends(),
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 404, "User not found"))
    # 🔥 Validate password match manually
    if request.password and request.password != request.confirm_password:
        return api_response(400, "Passwords do not match")

    if isinstance(request.image, StarletteUploadFile):
        if db_user.image:
            delete_media_items(session, filenames=[db_user.image["filename"]])

        files = [request.image]
        saved_files = await uploadImage(files, thumbnail=False)

        records = entryMedia(session, saved_files)

        request.image = records[0].model_dump(
            include={"id", "filename", "original", "media_type"}
        )

    else:
        if hasattr(request, "image"):
            delattr(request, "image")

    if (
        request.email
        and request.email != user.get("email")
        and exist_verified_email(session, request.email)
    ):
        return api_response(
            400,
            "This email is already registered and verified.",
        )

    updated_user = updateOp(db_user, request, session)

    if request.password:
        updated_user.password = hash_password(request.password)
    # ✅ Handle password hash only if password provided

    if request.phone and request.phone != user.get("phone"):
        updated_user.verified = False
    if request.email and request.email != user.get("email"):

        # ✅ Create JWT token (valid for lifetime)
        verify_token = create_access_token({"id": db_user.id, "email": db_user.email})
        updated_user.email_verified = False
        # Load template
        verify_url = f"{DOMAIN}/api/verify-email?verify_token={verify_token}"
        with open("src/templates/email_verification.html") as f:
            html_template = f.read().replace("{{VERIFY_URL}}", verify_url)
        send_email(
            to_email=db_user.email,
            subject="Verify Your Email Address",
            body=html_template,
        )

    session.commit()
    session.refresh(updated_user)
    return api_response(
        200, "User Update Successfully", UserRead.model_validate(updated_user)
    )
