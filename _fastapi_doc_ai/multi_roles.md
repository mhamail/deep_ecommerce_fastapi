# User Model # Relationships

user_roles: list["UserRole"] = Relationship(back_populates="user")

# Role Model

```py
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
```

## Security

```py

def require_signin(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer()),
) -> Dict:
    token = credentials.credentials  # Extract token from Authorization header

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user = payload.get("user")

        if user is None:
            api_response(
                status.HTTP_401_UNAUTHORIZED,
                "Invalid token: no user data",
            )

        if payload.get("refresh") is True:
            api_response(
                401,
                "Refresh token is not allowed for this route",
            )

        return user  # contains {"email": ..., "id": ...}

    except JWTError as e:
        print(e)
        return api_response(status.HTTP_401_UNAUTHORIZED, "Invalid token", data=str(e))

def verified_user(user: dict = Depends(require_signin)):
    if user.get("verified") is False or user.get("phone") is None:
        api_response(
            status.HTTP_423_LOCKED,
            "User is not verified",
        )
    return user

def get_user_permissions(user: dict) -> set[str]:
    roles = user.get("roles", [])

    permissions = set()
    for role in roles:
        permissions.update(role.get("permissions", []))

    return permissions


def has_role(user: dict, role_name: str) -> bool:
    roles = user.get("roles", [])
    return any(r.get("name") == role_name for r in roles)


def require_admin(
    user: dict = Depends(require_signin),
):
    try:
        roles = user.get("roles", [])

        if not roles and not user.get("is_root"):
            return api_response(
                status.HTTP_401_UNAUTHORIZED,
                "Access denied: no roles found",
            )

        user_permissions = get_user_permissions(user)

        # ✅ Admin logic
        if (
            not has_role(user, "root")
            and user.get("is_root") is False
            and "system:*" not in user_permissions
        ):
            return api_response(
                status.HTTP_403_FORBIDDEN,
                "Access denied: Admins only",
            )

        return user

    except JWTError:
        return api_response(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )


def require_permission(*permissions: str):
    def permission_checker(
        user: dict = Depends(require_signin),
    ):
        roles = user.get("roles", [])

        if not roles:
            return api_response(403, "Permission denied")

        user_permissions = get_user_permissions(user)

        # ✅ सुपर admin shortcut
        if "system:*" in user_permissions:
            return user

        # ✅ Match ANY permission
        if any(p in user_permissions for p in permissions):
            return user

        return api_response(403, "Permission denied")

    return permission_checker

```

# Test Auth

```py
@router.get("/testauth", response_model=dict)
def test_auth(
    user: requireSignin,
):
    return api_response(
        200,
        "Token is valid",
        {"user": user},
    )


@router.get("/testadmin")
def get_admin_data(
    user: requireAdmin,
):

    return {"message": f"Hello Admin {user['email']}", "user": user}


@router.get("/testpermission")
def get_admin_data(
    user=requirePermission("system:*"),
):
    return {"message": f"Hello Admin {user}"}

```
