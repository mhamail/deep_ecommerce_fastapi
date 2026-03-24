from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, EmailStr, model_validator
from sqlalchemy import JSON, Column, Enum
from sqlmodel import Field, Index, Relationship, SQLModel, text

from src.api.models.role_model.roleModel import RoleRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models.role_model.userRoleModel import UserRole

    from src.api.models.role_model.roleModel import Role


class UserPhone(SQLModel):
    # User enters this during registration
    unverified_phone: Optional[str] = Field(
        default=None, description="Temporary phone until verified"
    )

    # Saved only when fully verified
    phone: Optional[str] = Field(
        default=None, index=True, description="Verified unique phone"
    )

    verified: bool = Field(default=False)


class User(
    TimeStampedModel,
    UserPhone,
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

    country: str = Field(description="Country name (e.g., Pakistan)")
    country_code: str = Field(description="Country code (e.g., PK)")
    currency_code: str = Field(description="Currency code (e.g., PKR)")
    currency_symbol: str = Field(description="Currency symbol (e.g., ₨)")
    # Relationships
    user_roles: list["UserRole"] = Relationship(back_populates="user")

    __table_args__ = (
        # Conditional unique index for verified phones
        Index(
            "uq_users_phone_verified",
            "phone",
            unique=True,
            postgresql_where=text("verified = true"),
        ),
        # ✅ Unique verified email only
        Index(
            "uq_users_verified_email",
            "email",
            unique=True,
            postgresql_where=text("email_verified = true"),
        ),
    )

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
    full_name: str
    email: EmailStr
    phone: str
    password: str
    confirm_password: str
    country: str
    country_code: str
    currency_code: str
    currency_symbol: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values


class UserUpdateForm:
    def __init__(
        self,
        email: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        full_name: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        cnic: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        confirm_password: Optional[str] = Form(None),
        country: Optional[str] = Form(None),
        country_code: Optional[str] = Form(None),
        currency_code: Optional[str] = Form(None),
        currency_symbol: Optional[str] = Form(None),
        # image upload
        image: Optional[Union[UploadFile, str]] = File(None),
    ):
        # Convert empty → None
        def clean(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip() == "":
                return None
            return v

        self.email = clean(email)
        self.phone = clean(phone)
        self.full_name = clean(full_name)
        self.address = clean(address)
        self.cnic = clean(cnic)
        self.password = clean(password)
        self.confirm_password = clean(confirm_password)
        self.country = clean(country)
        self.country_code = clean(country_code)
        self.currency_code = clean(currency_code)
        self.currency_symbol = clean(currency_symbol)
        self.image: Optional[Union[UploadFile, str]] = image


class UserRoleRead(SQLModel):
    id: int
    name: str
    permissions: list[str]
    user_id: int


class UserReadBase(TimeStampReadModel):
    id: int
    full_name: str
    phone: str
    email: EmailStr
    email_verified: bool
    # is_active: bool
    is_root: bool
    image: Optional[Dict[str, Any]] = None
    contactinfo: Optional[Dict[str, Any]] = None
    country: str
    country_code: str
    currency_code: str
    currency_symbol: str


class UserRead(SQLModel, UserReadBase):
    roles: Optional[List[UserRoleRead]] = None
    pass


class LoginRequest(BaseModel):
    identifier: str  # phone OR email
    password: str
