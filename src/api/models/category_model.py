import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, EmailStr, model_validator
from sqlalchemy import JSON, Column, Enum
from sqlmodel import Field, Index, Relationship, SQLModel, text

from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import Product


class Category(TimeStampedModel, table=True):
    __tablename__ = "categories"

    # ==========================
    # Primary Fields
    # ==========================
    id: Optional[int] = Field(default=None, primary_key=True)

    # Category name (e.g. "Electronics", "Mobiles")
    name: str = Field(max_length=191, index=True)

    # URL-friendly unique identifier (e.g. "electronics", "mobiles")
    slug: str = Field(max_length=191, index=True, unique=True)

    # Hierarchy level:
    # 1 = Root category
    # 2 = Sub-category
    # 3 = Sub-sub-category
    level: int = Field(default=1, index=True)

    # Optional UI icon (string path or icon class)
    icon: Optional[str] = Field(default=None, max_length=191)

    # Category image (stored as JSON: url, alt, etc.)
    image: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Long description / details
    details: Optional[str] = Field(default=None)

    # ==========================
    # Hierarchy (Self-referencing)
    # ==========================

    # Direct parent (NULL for root categories)
    parent_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", index=True
    )

    # Root category reference (top-most ancestor)
    root_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", index=True
    )

    # ==========================
    # Business Fields
    # ==========================

    # Commission percentage for admin
    admin_commission_rate: Optional[float] = Field(default=None)

    # Active / inactive toggle
    is_active: bool = Field(default=True, index=True)

    # ==========================
    # Relationships
    # ==========================

    # Parent category
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "Category.id",
            "foreign_keys": "[Category.parent_id]",
        },
    )

    # Child categories
    children: List["Category"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "foreign_keys": "[Category.parent_id]",
            "cascade": "all, delete",  # optional: auto-delete children
        },
    )

    # Root category (top-level ancestor)
    root: Optional["Category"] = Relationship(
        back_populates="descendants",
        sa_relationship_kwargs={
            "remote_side": "Category.id",  # parent relationship → needs remote_side ✅
            "foreign_keys": "[Category.root_id]",  # root relationship   → also needs remote_side ✅
        },
    )

    # All descendants under same root
    descendants: List["Category"] = Relationship(
        back_populates="root",
        sa_relationship_kwargs={
            "foreign_keys": "[Category.root_id]",
        },
    )

    # Products under this category
    products: List["Product"] = Relationship(back_populates="category")


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=191)
    slug: str = Field(..., max_length=191)

    level: Optional[int] = 1

    icon: Optional[str] = None
    image: Optional[Dict[str, Any]] = None
    details: Optional[str] = None

    parent_id: Optional[int] = None
    root_id: Optional[int] = None

    admin_commission_rate: Optional[float] = None
    is_active: Optional[bool] = True


class CategoryRead(CategoryBase):
    id: int

    class Config:
        from_attributes = True


class CategoryTreeRead(CategoryRead):
    children: List["CategoryTreeRead"] = []


class CategoryForm(BaseModel):
    def __init__(
        self,
        name: str = Form(..., max_length=191),
        slug: str = Form(..., max_length=191),
        level: Optional[int] = Form(1),
        icon: Optional[str] = Form(None),
        image: Optional[Dict[str, Any]] = Form(None),
        details: Optional[str] = Form(None),
        parent_id: Optional[int] = Form(None),
    ):
        super().__init__()
