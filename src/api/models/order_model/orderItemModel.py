from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Order


class OrderItem(TimeStampedModel, table=True):
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)

    order_id: int = Field(
        foreign_key="orders.id",
        index=True,
    )

    shop_id: int = Field(
        foreign_key="shops.id",
        index=True,
    )

    product_id: int

    product_variant_id: int | None = None

    product_name: str

    quantity: int

    price: float
    actual_price: float

    variant_attributes: list | None = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )

    image: dict | None = Field(
        default=None,
        sa_column=Column(JSON),
    )

    # relationships
    order: "Order" = Relationship(back_populates="items")


class OrderItemsRead(SQLModel):
    id: int
    order_id: int
    product_id: Optional[int] = None
    shop_id: Optional[int] = None
    product_variant_id: Optional[int] = None
    product_name: str
    variant_attributes: Optional[dict] = None
    price: float
    actual_price: Optional[float] = None
    quantity: int
    image: Optional[dict] = None

    class Config:
        from_attributes = True
