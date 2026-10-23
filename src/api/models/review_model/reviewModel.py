from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field as PField
from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel
from src.api.models.userModel import User
from src.api.models.utils import mask_author


class ProductReview(TimeStampedModel, table=True):
    """One star rating (+ optional text) per customer per product. Edits
    replace it; the product's own aggregate (`Product.rating_*`) is
    recomputed on every write, so listings never aggregate on the fly."""

    __tablename__ = "product_reviews"
    __table_args__ = (
        UniqueConstraint("product_id", "user_id", name="uq_review_product_user"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("products.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )
    )
    user_id: int = Field(foreign_key="users.id", index=True)

    rating: int = Field(ge=1, le=5)

    comment: Optional[str] = Field(default=None, max_length=2000)

    # True when the reviewer has a delivered order containing this product,
    # decided once when the review is written.
    verified_purchase: bool = Field(default=False)

    user: Optional[User] = Relationship()

    @property
    def author_name(self) -> str:
        return mask_author(self.user)


# ==========================
# Read schemas
# ==========================
class ReviewRead(SQLModel):
    id: int
    product_id: int
    rating: int

    comment: Optional[str] = None
    verified_purchase: bool
    author_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class RatingSummary(BaseModel):
    average: float
    count: int
    # {"1": n, "2": n, ..., "5": n}
    breakdown: dict[str, int]


class MyReviewStatus(BaseModel):
    review: Optional[ReviewRead] = None
    # Would a new review from this customer carry the "Verified purchase" badge?
    can_verify: bool = False


# ==========================
# Request bodies (JSON)
# ==========================
class ReviewWrite(BaseModel):
    rating: int = PField(ge=1, le=5)
    comment: Optional[str] = PField(default=None, max_length=2000)
