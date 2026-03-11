from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import EmailStr, model_validator
from sqlalchemy import JSON, Column, Enum
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.role_model.roleModel import RoleRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import (
        UserRole,
        Role,
    )


class User(
    TimeStampedModel,
    table=True,
):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    email: EmailStr = Field(
        max_length=191, index=True, unique=True, description="Email address of the user"
    )

    email_verified: bool = Field(default=False, description="Email verification status")

    full_name: str = Field(index=True, description="Full name of the user")
    contactinfo: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    image: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="Image of the user"
    )
    is_root: bool = Field(default=False)
    is_active: bool = Field(default=True)
    password: str = Field(nullable=False, description="Hashed password")
    phone: Optional[str] = Field(
        max_length=30, index=True, unique=True, description="unique phone"
    )
    country: str = Field(description="Country name (e.g., Pakistan)")
    country_code: str = Field(description="Country code (e.g., PK)")
    currency_code: str = Field(description="Currency code (e.g., PKR)")
    currency_symbol: str = Field(description="Currency symbol (e.g., ₨)")
    # Relationships
    user_roles: list["UserRole"] = Relationship(back_populates="user")

    @property
    def roles(self) -> list["Role"]:
        """Return Role objects directly"""
        return [ur.role for ur in self.user_roles if ur.role]

    @property
    def role_names(self) -> list[str]:
        return [role.name for role in self.roles]

    @property
    def permissions(self) -> list[str]:
        perms = []
        for role in self.roles:
            perms.extend(role.permissions)
        return perms


class UserCreate(SQLModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values


class UserReadBase(TimeStampReadModel):
    id: int
    name: str
    phone: str
    email: EmailStr
    is_active: bool
    is_root: bool
    image: Optional[Dict[str, Any]] = None
    contactinfo: Optional[Dict[str, Any]] = None


class UserRead(UserReadBase):
    roles: List[RoleRead] = None
