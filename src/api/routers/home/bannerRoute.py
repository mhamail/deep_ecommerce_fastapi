from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import func, select

from src.api.core.dependencies import GetSession, requirePermission
from src.api.core.operation.media import deleteMediaFiles, uploadSingleMedia
from src.api.core.response import api_response, raiseExceptions
from src.api.models.home_model.homeModel import (
    BANNER_SECTION_TYPES,
    Banner,
    BannerForm,
    BannerRead,
    HomeSection,
    HomeSectionType,
    ReorderRequest,
)

router = APIRouter(prefix="/banner", tags=["Banner"])

PERMISSION = "homepage:manage"


def _check_link(link: str | None):
    """Only site-relative paths or http(s) URLs — never `javascript:` and
    friends, since this value ends up in an <a href> on the storefront."""
    if not link:
        return
    if link.startswith("/") and not link.startswith("//"):
        return
    if link.lower().startswith(("http://", "https://")):
        return
    api_response(400, "Link must start with '/' or http(s)://")


@router.post("/create")
async def create_banner(
    session: GetSession,
    request: BannerForm = Depends(),
    user=requirePermission(PERMISSION),
):
    raiseExceptions(
        (request.section_id, 400, "section_id is required"),
        (request.image, 400, "A banner needs an image"),
    )
    section = session.get(HomeSection, request.section_id)
    raiseExceptions((section, 404, "Section not found"))
    if HomeSectionType(section.type) not in BANNER_SECTION_TYPES:
        api_response(400, "This section type does not hold banners")
    _check_link(request.link_url)

    image = await uploadSingleMedia(request.image, session)
    raiseExceptions((image, 400, "Image upload failed"))

    last = session.exec(
        select(func.max(Banner.position)).where(Banner.section_id == section.id)
    ).one()
    banner = Banner(
        section_id=section.id,
        image=image,
        title=request.title or None,
        content=request.content or None,
        link_url=request.link_url or None,
        open_in_new_tab=bool(request.open_in_new_tab),
        is_active=True if request.is_active is None else request.is_active,
        position=(last if last is not None else -1) + 1,
    )
    session.add(banner)
    session.commit()
    session.refresh(banner)

    return api_response(200, "Banner created", BannerRead.model_validate(banner))


@router.put("/update/{id}")
async def update_banner(
    id: int,
    session: GetSession,
    request: BannerForm = Depends(),
    user=requirePermission(PERMISSION),
):
    banner = session.get(Banner, id)
    raiseExceptions((banner, 404, "Banner not found"))
    _check_link(request.link_url)

    if request.image:
        new_image = await uploadSingleMedia(request.image, session)
        raiseExceptions((new_image, 400, "Image upload failed"))
        await deleteMediaFiles(session, banner.image)  # replaced → free the old file
        banner.image = new_image

    # None = omitted (leave alone), "" = cleared.
    if request.title is not None:
        banner.title = request.title.strip() or None
    if request.content is not None:
        banner.content = request.content.strip() or None
    if request.link_url is not None:
        banner.link_url = request.link_url or None
    if request.open_in_new_tab is not None:
        banner.open_in_new_tab = request.open_in_new_tab
    if request.is_active is not None:
        banner.is_active = request.is_active

    banner.updated_at = datetime.now(timezone.utc)
    session.add(banner)
    session.commit()
    session.refresh(banner)

    return api_response(200, "Banner updated", BannerRead.model_validate(banner))


@router.delete("/delete/{id}")
async def delete_banner(
    id: int,
    session: GetSession,
    user=requirePermission(PERMISSION),
):
    banner = session.get(Banner, id)
    raiseExceptions((banner, 404, "Banner not found"))

    await deleteMediaFiles(session, banner.image)
    session.delete(banner)
    session.commit()

    return api_response(200, "Banner deleted")


@router.put("/reorder/{section_id}")
def reorder_banners(
    section_id: int,
    body: ReorderRequest,
    session: GetSession,
    user=requirePermission(PERMISSION),
):
    """`ids` is the full desired order of one section's banners."""
    banners = {
        b.id: b
        for b in session.exec(
            select(Banner).where(Banner.section_id == section_id)
        ).all()
    }
    raiseExceptions(
        (set(body.ids) <= set(banners), 400, "Unknown banner id in the order list")
    )
    for position, banner_id in enumerate(body.ids):
        banners[banner_id].position = position
        session.add(banners[banner_id])
    session.commit()

    return api_response(200, "Order saved")
