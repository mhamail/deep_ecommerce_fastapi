from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field as PField
from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel
from src.api.models.product_model.productModel import Product
from src.api.models.userModel import User
from src.api.models.utils import mask_author


class ProductQuestion(TimeStampedModel, table=True):
    """A customer question on a product; answered by the product's shop."""

    __tablename__ = "product_questions"

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

    question: str = Field(max_length=500)

    answer: Optional[str] = Field(default=None, max_length=2000)
    answered_by: Optional[int] = Field(default=None, foreign_key="users.id")
    answered_at: Optional[datetime] = None

    user: Optional[User] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ProductQuestion.user_id"}
    )
    product: Optional[Product] = Relationship()

    @property
    def product_name(self) -> Optional[str]:
        return self.product.name if self.product else None

    @property
    def author_name(self) -> str:
        return mask_author(self.user)


# ==========================
# Read schemas
# ==========================
class QuestionRead(SQLModel):
    id: int
    product_id: int
    question: str
    answer: Optional[str] = None
    answered_at: Optional[datetime] = None
    author_name: str
    created_at: datetime


class ShopQuestionRead(QuestionRead):
    """Shop-side row — adds the product name so one inbox can span products."""

    product_name: Optional[str] = None


class PendingQuestions(BaseModel):
    """Header-bell payload: how many questions still need an answer, plus
    the newest few."""

    count: int
    latest: list[ShopQuestionRead]


# ==========================
# Request bodies (JSON)
# ==========================
class QuestionCreate(BaseModel):
    question: str = PField(min_length=5, max_length=500)


class QuestionAnswer(BaseModel):
    answer: str = PField(min_length=1, max_length=2000)
