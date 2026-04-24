from typing import TYPE_CHECKING, Optional, List, Union
from fastapi import File, Form, UploadFile
from sqlmodel import JSON, SQLModel, Field, Relationship, Column


from src.api.models.mediaModel import MediaRead
from src.api.models.utils import clean, clean_json, to_bool, to_float, to_int
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Shop, User


class Product(TimeStampedModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relations
    shop_id: int = Field(foreign_key="shops.id", index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")

    # Basic Info
    name: str = Field(max_length=191, index=True)
    slug: str = Field(max_length=191, unique=True, index=True)
    description: Optional[str] = None

    # Pricing
    price: float = Field(default=0, index=True)
    discount_price: Optional[float] = Field(default=None)
    cost_price: Optional[float] = Field(default=None)

    # Inventory
    sku: Optional[str] = Field(default=None, max_length=100, index=True)
    stock: int = Field(default=0)
    is_in_stock: bool = Field(default=True)

    # Media
    thumbnail: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    images: Optional[List[dict]] = Field(default_factory=list, sa_column=Column(JSON))

    # Attributes & Variants (for filters)
    attributes: Optional[List[dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))

    # SEO
    meta_title: Optional[str] = Field(default=None, max_length=191)
    meta_description: Optional[str] = None

    # Status
    is_active: bool = Field(default=True)
    is_featured: bool = Field(default=False)

    # Relationships
    shop: "Shop" = Relationship(back_populates="products")
    creator: "User" = Relationship(back_populates="created_products")


class ProductRead(SQLModel, TimeStampReadModel):
    id: int
    # Basic
    name: str
    slug: str
    description: Optional[str] = None

    # Pricing
    price: float
    discount_price: Optional[float] = None

    # Inventory
    sku: Optional[str] = None
    stock: int
    is_in_stock: bool

    # Media
    thumbnail: Optional[MediaRead] = None
    images: Optional[List[Optional[MediaRead]]] = []

    # Attributes
    attributes: Optional[List[dict]] = []
    tags: Optional[List[str]] = []

    # SEO
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

    # Status
    is_active: bool
    is_featured: bool


class ProductForm:
    def __init__(
        self,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        discount_price: Optional[float] = Form(None),
        cost_price: Optional[float] = Form(None),
        sku: Optional[str] = Form(None),
        stock: Optional[int] = Form(None),
        is_active: Optional[bool] = Form(True),
        is_featured: Optional[bool] = Form(False),
        # Media
        thumbnail: Optional[Union[UploadFile, str]] = File(None),
        images: List[UploadFile] = File(None),
        # JSON fields
        attributes: Optional[str] = Form(None),
        tags: Optional[str] = Form(None),
        # SEO
        meta_title: Optional[str] = Form(None),
        meta_description: Optional[str] = Form(None),
    ):

        # ==========================
        # Assign values
        # ==========================
        self.name = clean(name)
        self.description = clean(description)

        self.price = to_float(price) or 0
        self.discount_price = to_float(discount_price)
        self.cost_price = to_float(cost_price)

        self.sku = clean(sku)
        self.stock = to_int(stock) or 0

        self.is_active = to_bool(is_active) if is_active is not None else True
        self.is_featured = to_bool(is_featured) if is_featured is not None else False

        # Media
        self.thumbnail = thumbnail
        self.images = images or []

        # JSON
        self.attributes = clean_json(attributes) or []
        self.tags = clean_json(tags) or []

        # SEO
        self.meta_title = clean(meta_title)
        self.meta_description = clean(meta_description)
