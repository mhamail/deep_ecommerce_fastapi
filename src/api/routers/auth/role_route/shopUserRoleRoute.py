from fastapi import APIRouter
from sqlmodel import select

from src.api.models.role_model.roleModel import Role
from src.api.core.operation import listRecords
from src.api.core.response import api_response, raiseExceptions
from src.api.core.dependencies import (
    GetSession,
    ListQueryParams,
    requireShopPermission,
    requireAdmin,
)
from src.api.models.role_model.userRoleModel import (
    UserRole,
    UserRoleCreate,
    UserRoleRead,
)

router = APIRouter(prefix="/user-role", tags=["Shop User Role"])


@router.post("/create-shop")
def create_role(
    request: UserRoleCreate,
    session: GetSession,
    user=requireShopPermission(["role_create"]),
):
    role = session.get(Role, request.role_id)
    raiseExceptions((role, 404, "Role not found"))
    default_shop = user.get("default_shop")
    if role.shop_id and role.shop_id != default_shop.id:
        return api_response(403, "You can only assign roles that you are belong to")
    user_role = UserRole(
        **request.model_dump()
    )  # Similar to new Role(req.body) in Mongoose

    if default_shop:
        user_role.shop_id = default_shop.id
    session.add(user_role)
    session.commit()
    session.refresh(user_role)
    return api_response(
        201, "Role Created Successfully", UserRoleRead.model_validate(user_role)
    )
