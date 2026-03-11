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
