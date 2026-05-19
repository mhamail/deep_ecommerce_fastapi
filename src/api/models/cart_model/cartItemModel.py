from typing import TYPE_CHECKING, Optional, List

from fastapi import Form
from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.mediaModel import MediaRead
from src.api.models.utils import clean_json, to_float, to_int
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Cart, Product, ProductVariant


class CartItem(TimeStampedModel, table=True):
    __tablename__ = "cart_items"

    id: Optional[int] = Field(default=None, primary_key=True)

    cart_id: int = Field(foreign_key="carts.id", index=True)
    product_id: Optional[int] = Field(
        default=None, foreign_key="products.id", index=True
    )
    product_variant_id: Optional[int] = Field(
        default=None, foreign_key="product_variants.id", index=True
    )

    # Cart Item Info
    price: Optional[float] = None
    quantity: int = Field(default=1)
    variant_attributes: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Optional media snapshot
    image: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    cart: "Cart" = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()
    variant: Optional["ProductVariant"] = Relationship()


class CartItemRead(SQLModel, TimeStampReadModel):
    id: int
    cart_id: int
    product_id: Optional[int] = None
    product_variant_id: Optional[int] = None
    price: Optional[float] = None
    quantity: int
    variant_attributes: Optional[dict] = None
    image: Optional[MediaRead] = None


class CartItemForm:
    def __init__(
        self,
        product_id: Optional[int] = Form(None),
        product_variant_id: Optional[int] = Form(None),
        price: Optional[float] = Form(None),
        quantity: Optional[int] = Form(1),
        variant_attributes: Optional[str] = Form(
            None,
            description="JSON object containing selected variant attributes.",
            examples=['{"color": "red", "size": "M"}'],
        ),
    ):
        self.product_id = to_int(product_id)
        self.product_variant_id = to_int(product_variant_id)
        self.price = to_float(price)
        self.quantity = to_int(quantity) or 1
        self.variant_attributes = (
            clean_json(variant_attributes) if variant_attributes is not None else None
        )
