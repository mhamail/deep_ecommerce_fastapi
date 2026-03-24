User Model # Relationships
user_roles: list["UserRole"] = Relationship(back_populates="user")

Role Model

class Role(TimeStampedModel, table=True):
**tablename** = "roles"
id: Optional[int] = Field(default=None, primary_key=True)
name: str = Field(max_length=50, unique=True)
slug: str = Field(max_length=60, unique=True, index=True)
description: Optional[str] = None
permissions: list[str] = Field(
default_factory=list,
sa_type=JSON,
)
user_id: int = Field(foreign_key="users.id")
is_active: bool = Field(default=True) # relationships
user_roles: list["UserRole"] = Relationship(back_populates="role")

    @property
    def roles(self):
        """Return roles directly (not UserRole objects)."""
        return [ur.role for ur in self.user_roles if ur.role]

if TYPE_CHECKING:
from src.api.models.userModel import User
from src.api.models.role_model.roleModel import Role

# Database Table Model

class UserRole(TimeStampedModel, table=True):
**tablename** = "user_roles"

    id: Optional[int] = Field(default=None, primary_key=True)  # type: ignore
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")

    # relationships
    user: "User" = Relationship(back_populates="user_roles")
    role: "Role" = Relationship(back_populates="user_roles")
