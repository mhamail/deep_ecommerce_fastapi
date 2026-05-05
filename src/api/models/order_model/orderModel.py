from typing import TYPE_CHECKING, Optional, List

from fastapi import Form
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON

from src.api.models.order_model.orderItemModel import OrderItemRead
from src.api.models.utils import clean, clean_json, to_float, to_int
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User, Shop, OrderItem


class Order(TimeStampedModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relations
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    shop_id: Optional[int] = Field(default=None, foreign_key="shops.id", index=True)

    # Order Info
    order_number: str = Field(index=True, unique=True)

    # Pricing Summary
    subtotal: float = Field(default=0)
    discount: float = Field(default=0)
    total: float = Field(default=0)

    # Status
    status: str = Field(default="pending", index=True)
    payment_status: str = Field(default="pending")

    # Address (snapshot)
    shipping_address: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    items: List["OrderItem"] = Relationship(back_populates="order")
    user: "User" = Relationship()
    shop: "Shop" = Relationship()


class OrderRead(SQLModel, TimeStampReadModel):
    id: int
    user_id: Optional[int] = None
    shop_id: Optional[int] = None
    order_number: str
    subtotal: float
    discount: float
    total: float
    status: str
    payment_status: str
    shipping_address: Optional[dict] = None
    items: List[OrderItemRead] = []


class OrderForm:
    def __init__(
        self,
        user_id: Optional[int] = Form(None),
        shop_id: Optional[int] = Form(22),
        status: Optional[str] = Form("pending"),
        payment_status: Optional[str] = Form("pending"),
        shipping_address: Optional[str] = Form(
            {
                "city": "Rawalpindi",
                "state": "Punjab",
                "Address": "house# 123, street# 3, British Colony",
                "phone": "923123456789",
            }
        ),
        items: Optional[str] = Form([{"product_variant_id": 0, "quantity": 1}]),
    ):
        self.user_id = to_int(user_id)
        self.shop_id = to_int(shop_id)
        self.status = clean(status) or "pending"
        self.payment_status = clean(payment_status) or "pending"
        self.shipping_address = (
            clean_json(shipping_address) if shipping_address is not None else None
        )
        self.items = clean_json(items) if items is not None else []
