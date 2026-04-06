from typing import TYPE_CHECKING, List, Optional

from pydantic import field_validator
from sqlalchemy import JSON
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum

from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models.role_model.userRoleModel import UserRole


class Role(TimeStampedModel, table=True):
    __tablename__ = "roles"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True)
    slug: str = Field(max_length=60, unique=True, index=True)
    description: Optional[str] = None
    permissions: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
    )
    user_id: int = Field(foreign_key="users.id")
    shop_id: Optional[int] = Field(default=None, foreign_key="shops.id", index=True)
    is_system: Optional[bool] = Field(default=False)  # root roles
    is_active: bool = Field(default=True)
    # relationships
    user_roles: list["UserRole"] = Relationship(back_populates="role")

    @property
    def roles(self):
        """Return roles directly (not UserRole objects)."""
        return [ur.role for ur in self.user_roles if ur.role]


class PermissionEnum(str, Enum):
    PRODUCT_CREATE = "product:create"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"

    ORDER_VIEW = "order:view"
    ORDER_UPDATE = "order:update"

    USER_MANAGE = "user:manage"


class RoleReadBase(TimeStampReadModel):
    id: int
    name: str
    slug: str
    permissions: list[str]
    user_id: int
    is_active: bool
    description: Optional[str]


class RoleRead(SQLModel, RoleReadBase):
    """Full role info returned in UserRead"""

    pass


class RoleCreate(SQLModel):
    name: str
    description: Optional[str] = None
    permissions: list[str] = []


class RoleUpdate(SQLModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None


class ShopRoleCreate(SQLModel):
    name: str
    permissions: List[PermissionEnum]

    @field_validator("permissions")
    def validate_permissions(cls, v):
        if not v:
            raise ValueError("At least one permission required")
        return list(set(v))
