from typing import TYPE_CHECKING, Literal, Optional


from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

# from api.models.role_model.roleModel import RoleRead
# from api.models.usersModel import UserReadBase
from src.api.models.baseModel import TimeStampedModel


if TYPE_CHECKING:
    from src.api.models import User, Role


#  Database Table Model
class UserRole(TimeStampedModel, table=True):
    __tablename__ = "user_roles"

    id: Optional[int] = Field(default=None, primary_key=True)  # type: ignore
    user_id: int = Field(foreign_key="users.id")
    role_id: int = Field(foreign_key="roles.id")

    # relationships
    user: "User" = Relationship(back_populates="user_roles")
    role: "Role" = Relationship(back_populates="user_roles")


# Request Schema/Pydantic Model
class UserRoleCreate(SQLModel):
    role_id: int
    user_id: int
