from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy.orm import selectinload
from sqlmodel import func, select

from src.api.core.dependencies import GetSession, requireSignin
from src.api.core.response import api_response, raiseExceptions
from src.api.core.security import get_user_permissions
from src.api.models.product_model.productModel import Product
from src.api.models.review_model.reviewModel import (
    MyReviewStatus,
    ProductReview,
    RatingSummary,
    ReviewRead,
    ReviewWrite,
)
from src.api.routers.review.fn import has_delivered_purchase, recompute_rating

router = APIRouter(prefix="/review", tags=["Review"])

PUBLIC_PAGE_LIMIT = 50
ADMIN_PERMISSIONS = {"system:*"}


# ==========================================================================
# helpers
# ==========================================================================
def _clean(text: str | None) -> str | None:
    """Reviews are plain text (the storefront renders them as text, never
    HTML) — trim and collapse empty to None."""
    text = (text or "").strip()
    return text or None


def _active_product(session, product_id: int) -> Product:
    product = session.get(Product, product_id)
    raiseExceptions((product and product.is_active, 404, "Product not found"))
    return product


def _is_site_admin(user: dict) -> bool:
    return bool(user.get("is_root") or get_user_permissions(user) & ADMIN_PERMISSIONS)


def _page(stmt, page: int, limit: int):
    return stmt.offset((page - 1) * limit).limit(limit)


# ==========================================================================
# reviews — public
# ==========================================================================
@router.get("/summary/{product_id}")
def rating_summary(product_id: int, session: GetSession):
    """Read straight from the product's stored aggregate — no aggregation
    query. Same numbers the product cards show."""
    product = _active_product(session, product_id)
    breakdown = {str(s): 0 for s in range(1, 6)} | (product.rating_breakdown or {})
    return api_response(
        200,
        "Rating summary",
        RatingSummary(
            average=product.rating_average,
            count=product.rating_count,
            breakdown=breakdown,
        ),
    )


@router.get("/public/{product_id}")
def public_reviews(
    product_id: int,
    session: GetSession,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=PUBLIC_PAGE_LIMIT),
    rating: int | None = Query(None, ge=1, le=5),
):
    stmt = select(ProductReview).where(ProductReview.product_id == product_id)
    if rating:
        stmt = stmt.where(ProductReview.rating == rating)

    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(
        _page(
            stmt.options(selectinload(ProductReview.user)).order_by(
                ProductReview.created_at.desc(), ProductReview.id.desc()
            ),
            page,
            limit,
        )
    ).all()

    return api_response(
        200, "Reviews found", [ReviewRead.model_validate(r) for r in rows], total
    )


# ==========================================================================
# reviews — signed-in customer
# ==========================================================================
@router.get("/mine/{product_id}")
def my_review(product_id: int, session: GetSession, user: requireSignin):
    """The viewer's own review of this product (if any) and whether a new
    one would be a verified purchase — drives the form's initial state."""
    review = session.exec(
        select(ProductReview)
        .options(selectinload(ProductReview.user))
        .where(
            ProductReview.product_id == product_id,
            ProductReview.user_id == user["id"],
        )
    ).first()
    return api_response(
        200,
        "Review status",
        MyReviewStatus(
            review=ReviewRead.model_validate(review) if review else None,
            can_verify=has_delivered_purchase(session, user["id"], product_id),
        ),
    )


@router.post("/create/{product_id}")
def create_review(
    product_id: int,
    request: ReviewWrite,
    session: GetSession,
    user: requireSignin,
):
    _active_product(session, product_id)

    exists = session.exec(
        select(ProductReview.id).where(
            ProductReview.product_id == product_id,
            ProductReview.user_id == user["id"],
        )
    ).first()
    if exists:
        api_response(409, "You already reviewed this product — edit your review")

    review = ProductReview(
        product_id=product_id,
        user_id=user["id"],
        rating=request.rating,
        comment=_clean(request.comment),
        verified_purchase=has_delivered_purchase(session, user["id"], product_id),
    )
    session.add(review)
    session.flush()
    recompute_rating(session, product_id)
    session.commit()
    session.refresh(review)

    return api_response(200, "Review added", ReviewRead.model_validate(review))


@router.put("/update/{id}")
def update_review(
    id: int,
    request: ReviewWrite,
    session: GetSession,
    user: requireSignin,
):
    review = session.get(ProductReview, id)
    raiseExceptions((review, 404, "Review not found"))
    if review.user_id != user["id"]:
        api_response(403, "You can only edit your own review")

    review.rating = request.rating
    review.comment = _clean(request.comment)
    review.updated_at = datetime.now(timezone.utc)
    session.add(review)
    session.flush()
    recompute_rating(session, review.product_id)
    session.commit()
    session.refresh(review)

    return api_response(200, "Review updated", ReviewRead.model_validate(review))


@router.delete("/delete/{id}")
def delete_review(id: int, session: GetSession, user: requireSignin):
    """The author, or a site admin moderating abuse."""
    review = session.get(ProductReview, id)
    raiseExceptions((review, 404, "Review not found"))
    if review.user_id != user["id"] and not _is_site_admin(user):
        api_response(403, "You can only delete your own review")

    product_id = review.product_id
    session.delete(review)
    session.flush()
    recompute_rating(session, product_id)
    session.commit()

    return api_response(200, "Review deleted")
