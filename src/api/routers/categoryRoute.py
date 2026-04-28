from typing import Optional

from fastapi import APIRouter, Depends, UploadFile
from sqlmodel import select
from src.api.core.operation.media import uploadMediaFiles
from src.api.core.utility import uniqueSlugify
from src.api.core.operation import listRecords, serialize_obj, updateOp
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import GetSession, requirePermission, requirePermission
from src.api.models.category_model import (
    Category,
    CategoryForm,
    CategoryRead,
    CategoryTreeRead,
)

router = APIRouter(prefix="/category", tags=["Category"])


def calculate_category_level(session, parent_id: Optional[int]) -> int:
    if not parent_id:
        return 1  # root level

    parent = session.get(Category, parent_id)
    if not parent:
        return api_response(400, "Parent category not found")

    if parent.level >= 3:
        return api_response(400, "Cannot create a category deeper than 3 levels")

    return parent.level + 1


@router.post("/create")
async def create(
    session: GetSession,
    request: CategoryForm = Depends(),
    user=requirePermission("category:create"),
):
    """Create a new category with auto-level and root assignment."""
    # 1️⃣ Calculate hierarchical level
    level = calculate_category_level(session, request.parent_id)
    # 2️⃣ Initialize model
    data = serialize_obj(request)
    await uploadMediaFiles(session, data, request)
    data = Category(**data, level=level)

    # 3️⃣ Generate unique slug
    data.slug = uniqueSlugify(session, Category, data.name)

    # add to session
    session.add(data)
    session.flush()  # assigns 'id' without committing

    # 4️⃣ Determine root_id
    if data.parent_id is None:
        data.root_id = data.id  # top-level category
    else:
        parent = session.get(Category, data.parent_id)
        data.root_id = parent.root_id if parent.root_id else parent.id

        # Top-level root fix
    if data.root_id is None:
        data.root_id = data.id

    session.commit()  # commit everything in one transaction
    session.refresh(data)

    return api_response(
        200, "Category Created Successfully", CategoryRead.model_validate(data)
    )


@router.get(
    "/read/{id_slug}",
    description="Category ID (int) or slug (str)",
    response_model=CategoryTreeRead,
)
def get(id_slug: str, session: GetSession):
    # Check if it's an integer ID
    if id_slug.isdigit():
        read = session.get(Category, int(id_slug))
    else:
        # Otherwise treat as slug
        read = (
            session.exec(select(Category).where(Category.slug.ilike(id_slug)))
            .scalars()
            .first()
        )
    raiseExceptions((read, 404, "Category not found"))

    return api_response(200, "Category Found", CategoryTreeRead.model_validate(read))
