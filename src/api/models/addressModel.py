from typing import Optional

from pydantic import BaseModel, Field as PydanticField
from sqlmodel import JSON, Column, Field

from src.api.models.baseModel import TimeStampedModel


class AddressDetail(BaseModel):
    street: str = PydanticField(..., max_length=191)
    city: str = PydanticField(..., max_length=191)
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class Location(BaseModel):
    lat: Optional[float] = None  # Make optional
    lng: Optional[float] = None  # Make optional


class user_address(
    TimeStampedModel,
    table=True,
):
    __tablename__ = "user_addresses"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    address: AddressDetail = Field(sa_column=Column(JSON))
    location: Optional[Location] = Field(default=None, sa_column=Column(JSON))
    default: bool = Field(default=False)
