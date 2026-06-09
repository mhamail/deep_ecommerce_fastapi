from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field as PydanticField, field_validator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel

if TYPE_CHECKING:
    from src.api.models.userModel import User


class AddressDetail(BaseModel):
    city: str = PydanticField(..., max_length=191)

    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    details: str = PydanticField(..., max_length=250)


class Location(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class UserAddress(
    TimeStampedModel,
    table=True,
):
    __tablename__ = "user_addresses"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    address: AddressDetail = Field(sa_column=Column(JSON))
    location: Optional[Location] = Field(default=None, sa_column=Column(JSON))
    default: int = Field(default=False, index=True)

    user: Optional["User"] = Relationship(back_populates="addresses")


class AddressBase(SQLModel):
    address: AddressDetail
    location: Optional[Location] = None


class AddressCreate(AddressBase):
    default: Optional[int] = PydanticField(default=None, ge=0, le=1)

    @field_validator("default", mode="before")
    @classmethod
    def default_to_int(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        return value


class AddressUpdate(SQLModel):
    address: Optional[AddressDetail] = None
    location: Optional[Location] = None
    default: Optional[int] = PydanticField(default=None, ge=0, le=1)

    @field_validator("default", mode="before")
    @classmethod
    def default_to_int(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return 1 if value else 0
        return value


class AddressRead(AddressBase):
    id: int
    user_id: int
    default: int = 1

    class Config:
        from_attributes = True


user_address = UserAddress
