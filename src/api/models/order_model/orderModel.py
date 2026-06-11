from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Column, JSON, String, text
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.addressModel import AddressDetail
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User, Shop


class Order(TimeStampedModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relations
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)

    # Order Info
    order_number: str = Field(
        sa_column=Column(
            String,
            nullable=False,
            unique=True,
            index=True,
            default=text("nextval('order_number_seq')::text"),
            server_default=text("nextval('order_number_seq')::text"),
        ),
    )

    # Pricing Summary
    subtotal: float = Field(default=0)
    discount: float = Field(default=0)
    total: float = Field(default=0)

    # Status
    status: str = Field(default="pending", index=True)
    payment_status: str = Field(default="pending")

    # Address (snapshot)
    shipping_address: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Item snapshots
    items: List[dict] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )

    # Relationships
    user: "User" = Relationship()


class OrderItemSnapshotRead(SQLModel):
    product_id: Optional[int] = None
    shop_id: Optional[int] = None
    product_variant_id: Optional[int] = None
    product_name: str
    variant_attributes: Optional[dict] = None
    price: float
    actual_price: Optional[float] = None
    quantity: int
    image: Optional[dict] = None
    line_total: float


class OrderRead(SQLModel, TimeStampReadModel):
    id: int
    user_id: Optional[int] = None
    order_number: str
    subtotal: float
    discount: float
    total: float
    status: str
    payment_status: str
    shipping_address: Optional[dict] = None
    items: List[OrderItemSnapshotRead] = Field(default_factory=list)


class OrderCreate(SQLModel):
    user_id: Optional[int] = None

    # ── Cart-based order ──────────────────────────────────────────────────────
    # Pass cart item IDs — shipping address auto-fetched from user's default address.
    cart_item_ids: Optional[List[int]] = Field(
        default=None,
        description="Cart item IDs to order. Shipping address is auto-populated from user's default address.",
        # examples=[[1, 2, 3]],
    )

    # ── Manual order ──────────────────────────────────────────────────────────
    items: Optional[List[dict]] = Field(
        default_factory=list,
        description="[{product_variant_id, quantity}]",
        # examples=[[{"product_variant_id": 1, "quantity": 2}]],
    )

    # ── Shared ────────────────────────────────────────────────────────────────
    discount: Optional[float] = 0
    status: Optional[str] = "pending"
    payment_status: Optional[str] = "pending"
    shipping_address: Optional[AddressDetail] = {
        "details": "",
        "phone": "",
        "person_name": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": "",
    }
