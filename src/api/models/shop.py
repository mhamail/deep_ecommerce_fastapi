from typing import TYPE_CHECKING, Optional, Union

from fastapi import File, Form, UploadFile
from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.mediaModel import MediaRead
from src.api.models.utils import clean, clean_json
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User


class Shop(TimeStampedModel, table=True):
    __tablename__ = "shops"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", unique=True)
    name: str = Field(default=None, max_length=191, unique=True)
    slug: str = Field(default=None, max_length=191, index=True, unique=True)
    description: Optional[str] = None
    cover_image: Optional[dict] = Field(
        default=None, sa_column=Column(JSON), description="Cover Image"
    )
    logo: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    is_active: bool = Field(default=False)
    address: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Relationships
    owner: "User" = Relationship(back_populates="shop")


class ShopForm(SQLModel):
    def __init__(
        self,
        owner_id: Optional[str] = Form(None),
        name: Optional[str] = Form(None),
        slug: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        cover_image: Optional[Union[UploadFile, str]] = File(None),
        logo: Optional[Union[UploadFile, str]] = File(None),
        address: Optional[dict] = Form(None),
    ):
        self.owner_id = clean(owner_id)
        self.name = clean(name)
        self.slug = clean(slug)
        self.description = clean(description)
        self.cover_image = cover_image
        self.logo = logo
        self.address = clean_json(address)


class RideRead(SQLModel, TimeStampReadModel):
    id: Optional[int]
    name: str
    slug: str
    description: str
    address: Optional[dict] = None
    cover_image: Optional[MediaRead] = None
    logo: Optional[MediaRead] = None
    is_active: bool
