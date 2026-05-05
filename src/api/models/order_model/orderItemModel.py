from typing import TYPE_CHECKING, Optional, Union

from fastapi import File, Form, UploadFile
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, JSON

from src.api.models.mediaModel import MediaRead
from src.api.models.utils import clean, clean_json, to_float, to_int
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import ProductVariant, Order, Product


class OrderItem(TimeStampedModel, table=True):
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)

    order_id: int = Field(foreign_key="orders.id", index=True)

    product_id: Optional[int] = Field(default=None, foreign_key="products.id", index=True)

    # IMPORTANT: link to variant
    product_variant_id: Optional[int] = Field(
        default=None, foreign_key="product_variants.id"
    )

    # Snapshot fields (VERY IMPORTANT)
    product_name: str
    variant_attributes: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    price: float
    quantity: int

    # Optional media snapshot
    image: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    order: "Order" = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()
    variant: "ProductVariant" = Relationship()


class OrderItemRead(SQLModel, TimeStampReadModel):
    id: int
    order_id: int
    product_id: Optional[int] = None
    product_variant_id: Optional[int] = None
    product_name: str
    variant_attributes: Optional[dict] = None
    price: float
    quantity: int
    image: Optional[MediaRead] = None


class OrderItemForm:
    def __init__(
        self,
        product_id: Optional[int] = Form(None),
        product_variant_id: Optional[int] = Form(None),
        product_name: Optional[str] = Form(None),
        variant_attributes: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        quantity: Optional[int] = Form(1),
        image: Optional[Union[UploadFile, str]] = File(None),
    ):
        self.product_id = to_int(product_id)
        self.product_variant_id = to_int(product_variant_id)
        self.product_name = clean(product_name)
        self.variant_attributes = (
            clean_json(variant_attributes) if variant_attributes is not None else None
        )
        self.price = to_float(price)
        self.quantity = to_int(quantity) or 1
        self.image = image
