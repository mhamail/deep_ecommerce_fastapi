from typing import TYPE_CHECKING, Optional, List, Union
from fastapi import File, Form, UploadFile
from pydantic import computed_field
from sqlmodel import JSON, SQLModel, Field, Relationship, Column


from src.api.models.product_model.ProductVariantModel import ProductVariantRead
from src.api.models.mediaModel import MediaRead
from src.api.models.utils import clean, clean_json, to_bool, to_float, to_int
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Shop, User, Category, ProductVariant


class Product(TimeStampedModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relations
    shop_id: int = Field(foreign_key="shops.id", index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    category_id: int = Field(foreign_key="categories.id", index=True)

    # Basic Info
    name: str = Field(max_length=191, index=True)
    slug: str = Field(max_length=191, unique=True, index=True)
    description: Optional[str] = None

    # Media
    thumbnail: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    images: Optional[List[dict]] = Field(default_factory=list, sa_column=Column(JSON))

    # Attributes & Variants (for filters)
    attributes: Optional[List[dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    # Example :[
    #   {"name": "brand", "value": "Nike"},
    #   {"name": "material", "value": "Cotton"}
    # ]
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
    category: "Category" = Relationship(back_populates="products")
    variants: List["ProductVariant"] = Relationship(back_populates="product")

    @property
    def min_price(self) -> Optional[float]:
        prices = [v.price for v in self.variants if v.price is not None]
        return min(prices) if prices else None

    @property
    def max_price(self) -> Optional[float]:
        prices = [v.price for v in self.variants if v.price is not None]
        return max(prices) if prices else None

    @property
    def min_discount_price(self) -> Optional[float]:
        prices = [v.discount_price for v in self.variants if v.discount_price is not None]
        return min(prices) if prices else None

    @property
    def max_discount_price(self) -> Optional[float]:
        prices = [v.discount_price for v in self.variants if v.discount_price is not None]
        return max(prices) if prices else None

    @property
    def total_stock(self) -> int:
        return sum(variant.stock or 0 for variant in self.variants)

    @property
    def min_price(self) -> Optional[float]:
        prices = [
            variant.discount_price or variant.price
            for variant in self.variants
            if variant.discount_price is not None or variant.price is not None
        ]
        return min(prices) if prices else None

    @property
    def max_price(self) -> Optional[float]:
        prices = [
            variant.discount_price or variant.price
            for variant in self.variants
            if variant.discount_price is not None or variant.price is not None
        ]
        return max(prices) if prices else None


class ShopRead(SQLModel):
    id: int
    name: str


class CategoryRead(SQLModel):
    id: int
    name: str
    root_id: int


class ProductBase(SQLModel):
    id: int
    # Basic
    name: str
    slug: str
    description: Optional[str] = None

    # Media
    thumbnail: Optional[MediaRead] = None
    # images: Optional[List[Optional[MediaRead]]] = None

    # Attributes
    attributes: Optional[List[dict]] = [{"name": "", "value": ""}]
    tags: Optional[List[str]] = []

    # SEO
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

    # Status
    is_active: bool
    is_featured: bool

    # variant
    min_price: Optional[float] = 0
    max_price: Optional[float] = 0
    total_stock: int = 0

    # Relations
    shop: ShopRead
    category: CategoryRead


class ProductVariantBase(SQLModel):
    id: int
    price: Optional[float]
    discount_price: Optional[float]
    stock: Optional[int]
    is_in_stock: Optional[bool]
    image: Optional[MediaRead]

    attributes: Optional[dict]


class ProductRead(ProductBase, TimeStampReadModel):
    variants: Optional[List[ProductVariantBase]] = None


class ProductSingleRead(ProductBase, TimeStampReadModel):
    variants: Optional[List[ProductVariantRead]] = None


class ProductForm:
    def __init__(
        self,
        # Basic Info
        name: Optional[str] = Form(""),
        description: Optional[str] = Form(""),
        # Status
        is_active: Optional[bool] = Form(True),
        is_featured: Optional[bool] = Form(False),
        # Media
        thumbnail: Optional[Union[UploadFile, str]] = File(None),
        delete_images: Optional[List[str]] = Form(None),
        # JSON fields
        attributes: Optional[str] = Form(None),
        # Example: [{"name": "color", "value": "red"}, {"name": "size", "value": "M"}]
        tags: Optional[str] = Form(None),
        # Variants
        variant_data: Optional[str] = Form(
            None,
            description="JSON array of product variants.",
            examples=[
                '[{"price": 1000, "discount_price": 900, "stock": 10, "sku": "TSHIRT-RED-M", "attributes": {"color": "red", "size": "M"}}]'
            ],
        ),
        # Example [{"price":200,"stock":2,"attribute":{"size":"xl"}}]
        # SEO
        meta_title: Optional[str] = Form(""),
        meta_description: Optional[str] = Form(""),
        # relations
        category_id: Optional[int] = Form(None),
    ):

        # ==========================
        # Assign values
        # ==========================
        self.name = clean(name)
        self.description = clean(description)

        self.is_active = to_bool(is_active) if is_active is not None else True
        self.is_featured = to_bool(is_featured) if is_featured is not None else False

        # Media
        self.thumbnail = thumbnail
        # self.images = images or []
        self.delete_images = clean(delete_images)

        # JSON
        self.attributes = clean_json(attributes) or []
        self.tags = clean_json(tags) or []
        self.variant_data = clean_json(variant_data)

        # SEO
        self.meta_title = clean(meta_title)
        self.meta_description = clean(meta_description)
        # relations
        self.category_id = category_id
