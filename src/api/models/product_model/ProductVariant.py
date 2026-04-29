from typing import TYPE_CHECKING, Optional, List, Union
from fastapi import File, Form, UploadFile
from pydantic import BaseModel
from sqlmodel import JSON, SQLModel, Field, Relationship, Column


from src.api.models.mediaModel import MediaRead
from src.api.models.utils import clean, clean_json, to_bool, to_float, to_int
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Product


class ProductVariant(TimeStampedModel, table=True):
    __tablename__ = "product_variants"

    id: Optional[int] = Field(default=None, primary_key=True)

    product_id: int = Field(foreign_key="products.id", index=True)

    # Variant Identity
    sku: Optional[str] = Field(default=None, index=True)

    # Pricing (override product)
    price: Optional[float] = None
    discount_price: Optional[float] = None

    # Inventory
    stock: int = Field(default=0)
    is_in_stock: bool = Field(default=True)

    # Variant Attributes (IMPORTANT)
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSON))
    # Example: {"color": "Red", "size": "M"}

    # Media
    image: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    product: "Product" = Relationship(back_populates="variants")


class ProductVariantForm:
    def __init__(
        self,
        # -------------------------
        # Relations
        # -------------------------
        product_id: Optional[int] = Form(None),
        # -------------------------
        # Variant Identity
        # -------------------------
        sku: Optional[str] = Form(None),
        # -------------------------
        # Pricing
        # -------------------------
        price: Optional[float] = Form(None),
        discount_price: Optional[float] = Form(None),
        # -------------------------
        # Inventory
        # -------------------------
        stock: Optional[int] = Form(None),
        is_in_stock: Optional[bool] = Form(True),
        # -------------------------
        # Media
        # -------------------------
        image: Optional[Union[UploadFile, str]] = File(None),
        # -------------------------
        # JSON Fields
        # -------------------------
        attributes: Optional[str] = Form(None),  # JSON string
        # -------------------------
        # Status
        # -------------------------
        is_active: Optional[bool] = Form(True),
    ):

        # ==========================
        # Assign values
        # ==========================
        self.product_id = to_int(product_id)

        self.sku = clean(sku)

        self.price = to_float(price)
        self.discount_price = to_float(discount_price)

        self.stock = to_int(stock) or 0
        self.is_in_stock = to_bool(is_in_stock) if is_in_stock is not None else True

        # Media
        self.image = image

        # JSON
        self.attributes = clean_json(attributes) or {}

        # Status
        self.is_active = to_bool(is_active) if is_active is not None else True
