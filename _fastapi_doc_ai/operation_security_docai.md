# My way to code Fastapi Doc Ai For Operation,Security Func, Media etc

## in this project we use latest fastapi method, uv package manager, sql model for schemas

## Operations

//=========================================

## Update Operation

// =======================================

```
from src.api.core.operation import listRecords, updateOp
```

```py
# Update only the fields that are provided in the request
# customFields = ["phone", "firstname", "lastname", "email"]
def updateOp(
    instance,
    request,
    session,
    customFields=None,
):
    # CASE 1: Only update custom fields
    if customFields:
        for field in customFields:
            if hasattr(request, field):
                value = getattr(request, field)
                if value is not None:
                    setattr(instance, field, value)

    else:
        # CASE 2: Auto-update all fields
        # Handle both Pydantic models AND plain classes
        if hasattr(request, "model_dump"):
            # Pydantic / SQLModel
            data = request.model_dump(exclude_unset=True)
        else:
            # Plain Class: extract fields with vars()
            data = {
                key: value for key, value in vars(request).items() if value is not None
            }

        # Apply updates
        for key, value in data.items():
            if hasattr(instance, key):  # if the key is in the model
                setattr(instance, key, value)

    # Update timestamp
    if hasattr(instance, "updated_at"):
        instance.updated_at = datetime.now(timezone.utc)

    session.add(instance)
    return instance

```

<!-- //////////////////////////////////// -->

# Scalor

<!-- ////////////////////////////////////////// -->

```py
def _exec(session, statement, Model):
    result = session.exec(statement)
    # If it's already Model objects, just return .all()
    if isinstance(result, ScalarResult):  # SQLAlchemy 2.x ScalarResult
        return result.all()
    else:
        # Fallback: try scalars (for select(Model))
        try:
            return result.scalars().all()
        except Exception:
            return result.all()
```

<!-- /////////////////////////////////////////// -->

# Media

<!-- ///////////////////////////////////////////// -->

```py
# Model
class Media(TimeStampedModel, table=True):
    __tablename__ = "media"
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    extension: str
    original: str
    media_type: str  # "image" | "video" | "doc"
    size_mb: Optional[float] = Field(default=None)
    thumbnail: Optional[str] = Field(default=None)


class MediaRead(BaseModel):
    id: int
    filename: str
    # extension: Optional[str] = None
    original: str
    # size_mb: Optional[float] = None
    thumbnail: Optional[str] = None
    media_type: str

    @field_serializer("original")
    def add_domain_to_url(self, v: Optional[str], _info):
        return f"{DOMAIN}{v}" if v else None

    @field_serializer("thumbnail")
    def add_domain_to_thumbnail(self, v: Optional[str], _info):
        return f"{DOMAIN}{v}" if v else None

    class Config:
        from_attributes = True

# Reusable Function
import os
import time
from src.api.core.response import api_response
from PIL import Image, UnidentifiedImageError, ImageOps

from src.api.core.dependencies import GetSession
from src.api.models.mediaModel import Media
from sqlalchemy import func
import os
from typing import List, Optional, TypedDict
from sqlmodel import select

BASE_DIR = "/var/www"
SUB_DIR = "travelmedia"
MEDIA_DIR = os.path.join(BASE_DIR, SUB_DIR)

ALLOWED_RAW_EXT = [".webp", ".avif", ".ico", ".svg"]
MAX_SIZE = 2 * 1024 * 1024  # 1 MB
THUMBNAIL_SIZE = (300, 300)  # max width/height
MAX_SIZE_MB = MAX_SIZE / (1024 * 1024)


class MediaType(TypedDict):
    filename: str
    extension: str
    original: str
    size_mb: float
    thumbnail: Optional[str]
    media_type: str


def entryMedia(session: GetSession, files: List[MediaType]):
    records = []
    for file_info in files:
        existing_media = session.scalar(
            select(Media).where(Media.filename == file_info["filename"])
        )
        print(existing_media)

        if existing_media:
            # ✅ Update existing record
            existing_media.extension = file_info["extension"]
            existing_media.original = file_info["original"]
            existing_media.size_mb = file_info["size_mb"]
            existing_media.thumbnail = file_info.get("thumbnail")
            existing_media.media_type = "image"
            session.add(existing_media)
            records.append(existing_media)
        else:
            # ✅ Create new record
            media = Media(
                filename=file_info["filename"],
                extension=file_info["extension"],
                original=file_info["original"],
                size_mb=file_info["size_mb"],
                thumbnail=file_info.get("thumbnail"),
                media_type="image",
            )
            session.add(media)
            session.flush()  # ensures ID assigned
            records.append(media)
    return records


async def uploadImage(files, thumbnail, unique=True):
    saved_files = []

    for file in files:
        original_name = os.path.splitext(file.filename)[0]
        ext = os.path.splitext(file.filename)[1].lower()

        timestamp = str(int(time.time() * 1000))

        # Apply unique filename BEFORE any conversion
        if unique:
            base_name = f"{original_name}-{timestamp}"
        else:
            base_name = original_name

        # RAW image handling
        if ext in ALLOWED_RAW_EXT:
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
        else:
            try:
                img = Image.open(file.file)
                icc_profile = img.info.get("icc_profile")

                img = ImageOps.exif_transpose(img)

                # Convert to webp with unique naming
                output_filename = base_name + ".webp"
                file_path = os.path.join(MEDIA_DIR, output_filename)

                img.save(
                    file_path,
                    "webp",
                    quality=95,
                    method=6,
                    icc_profile=icc_profile,
                    lossless=False,
                )
                ext = ".webp"

            except UnidentifiedImageError:
                raise api_response(
                    400,
                    f"File type {ext} is not a supported image format.",
                )

        # Validate file size
        size_bytes = os.path.getsize(file_path)
        if size_bytes > MAX_SIZE:
            os.remove(file_path)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            return api_response(
                400,
                f"{file.filename} is still larger than {MAX_SIZE_MB} MB after optimization ({size_mb} MB)",
            )

        # File info response
        file_info = {
            "filename": os.path.basename(file_path),
            "extension": ext,
            "original": f"/media/{os.path.basename(file_path)}",
            "size_mb": round(size_bytes / (1024 * 1024), 2),
        }

        # Thumbnail creation
        if thumbnail and ext in [".jpg", ".jpeg", ".png", ".webp"]:
            thumb_name = base_name + "_thumb.webp"
            thumb_path = os.path.join(MEDIA_DIR, thumb_name)

            with Image.open(file_path) as thumb:
                thumb.thumbnail(THUMBNAIL_SIZE)
                thumb.save(
                    thumb_path,
                    "webp",
                    quality=85,
                    method=6,
                )

            file_info["thumbnail"] = f"/media/{thumb_name}"

        saved_files.append(file_info)

    return saved_files


def delete_media_items(
    session: GetSession,
    ids: Optional[List[int]] = None,
    filenames: Optional[List[str]] = None,
) -> dict:
    """
    Delete media by IDs or filenames.
    - Skips deletion for media referenced in MediaTrack.
    - Removes files + thumbnails from disk and deletes DB rows.
    Returns a dict with deleted and skipped items.
    """
    if not ids and not filenames:
        raise ValueError("Must provide either ids or filenames to delete.")

    stmt = select(Media)
    if ids:
        stmt = stmt.where(Media.id.in_(ids))
    if filenames:
        stmt = stmt.where(
            func.lower(Media.filename).in_([f.lower() for f in filenames])
        )

    media_records = session.exec(stmt).all()
    if not media_records:
        return {"deleted": [], "skipped": [], "message": "No matching media found."}

    deleted_files = []

    for media in media_records:
        # --- Delete original file ---
        file_path = os.path.join(MEDIA_DIR, media.filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass  # silently ignore file deletion error

        # -------------------------
        # Delete thumbnail
        # -------------------------
        if media.thumbnail:
            thumb_path = os.path.join(MEDIA_DIR, os.path.basename(media.thumbnail))
        else:
            base, _ = os.path.splitext(media.filename)
            thumb_path = os.path.join(MEDIA_DIR, f"{base}_thumb.webp")

        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass  # ignore thumbnail deletion error

        # --- Remove from DB ---
        session.delete(media)
        deleted_files.append(media.filename)

    session.flush()

    message = "Media deletion completed."

    return {
        "deleted": deleted_files,
        "message": message,
    }

```

<!-- ///////////////////////////////// -->

# How to Use of Media in Form

<!-- ///////////////////////////////////// -->

```py
class UserRideForm:
    def __init__(
        self,
        # file upload
        car_pic: Optional[Union[UploadFile, str]] = File(None),
        other_images: List[UploadFile] = File(default=[]),
        delete_images: Optional[List[str]] = Form(None),
    ):
        # Convert empty → None
        # Convert empty string → None
        def clean(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip() == "":
                return None
            return v

        # Convert "true"/"false"/"1"/"0" → boolean
        def to_bool(v):
            v = clean(v)
            if v is None:
                return None
            val = str(v).lower()
            if val in ["true", "1", "yes"]:
                return True
            if val in ["false", "0", "no"]:
                return False
            return None  # fallback

        # Convert JSON string → dict
        def clean_json(v):

            v = clean(v)
            if v is None:
                return None
            try:
                return json.loads(v)
            except Exception:
                raise ValueError(f"Invalid JSON: {v}")

        # Convert to int
        def to_int(v):
            v = clean(v)
            if v is None:
                return None
            try:
                return int(v)
            except:
                return None

        # Convert to float
        def to_float(v):
            v = clean(v)
            if v is None:
                return None
            try:
                return float(v)
            except:
                return None

        # Assign fields
        # normalize empty string → None
        self.car_pic = car_pic

        # ✅ Better normalization
        self.other_images = other_images or []  # ✅ Simple fallback

        self.delete_images = clean(delete_images)

```

//=========================================

## Security

// =======================================

```py
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select
from sqlmodel import Session
from fastapi import (
    Depends,
    Header,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from src.api.core.response import api_response
from src.api.models import User

ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


## get user
def exist_user(db: Session, email: str):
    user = db.exec(select(User).where(User.email == email)).first()
    return user


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict,
    refresh: Optional[bool] = False,
    expires: Optional[timedelta] = None,
):

    if refresh:
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        expire = datetime.now(timezone.utc) + (
            expires or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

    payload = {
        "user": user_data,
        "exp": expire,
        "refresh": refresh,
    }
    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token(
    token: str,
) -> Optional[Dict]:
    try:
        decode = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # Ensure expiration is verified
        )

        return decode

    except JWTError as e:
        print(f"Token decoding failed: {e}")
        return None


def is_authenticated(authorization: Optional[str] = Header(None)):
    """
    Extract user from Bearer token.
    Return None if token is missing or invalid.
    """
    if not authorization:
        return None  # No token means offline or guest user

    # Expect format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # verifies expiration
        )
        user = payload.get("user")
        return user
    except JWTError:
        return None


def require_signin(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
) -> Dict:
    token = credentials.credentials  # Extract token from Authorization header

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user = payload.get("user")

        if user is None:
            api_response(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid token: no user data",
            )

        if payload.get("refresh") is True:
            api_response(
                401,
                "Refresh token is not allowed for this route",
            )

        return user  # contains {"email": ..., "id": ...}

    except JWTError as e:
        print(e)
        return api_response(status.HTTP_401_UNAUTHORIZED, "Invalid token", data=str(e))


def require_admin(user: dict = Depends(require_signin)):
    roles: List[str] = user.get("roles", [])
    if "root" not in roles:
        api_response(status.HTTP_403_FORBIDDEN, "Root User only")
    return user


def require_permission(*permissions: str):
    def permission_checker(user: dict = Depends(require_signin)):
        user_permissions: List[str] = user.get("permissions", [])

        # ✅ system:* always passes
        if "system:*" in user_permissions:
            return user

        # ✅ OR logic: check if user has any required permission
        if any(p in user_permissions for p in permissions):
            return user

        # ❌ no match → deny
        api_response(status.HTTP_403_FORBIDDEN, "Permission denied")

    return permission_checker

```
