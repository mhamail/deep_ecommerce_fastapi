from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select
from sqlmodel import Session
from fastapi import (
    Depends,
    HTTPException,
    Header,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from src.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE
from src.api.core.response import api_response


ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


## get user
def exist_user(db: Session, email: str):
    from src.api.models.userModel import User

    user = db.exec(select(User).where(User.email == email)).first()
    return user


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict,
    refresh: Optional[bool] = False,
    expires: Optional[timedelta] = None,
):

    if refresh:
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        expire = datetime.now(timezone.utc) + (
            expires or timedelta(days=ACCESS_TOKEN_EXPIRE)
        )

    payload = {
        "user": user_data,
        "exp": expire,
        "refresh": refresh,
    }
    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token(
    token: str,
) -> Optional[Dict]:
    try:
        decode = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # Ensure expiration is verified
        )

        return decode

    except JWTError as e:
        print(f"Token decoding failed: {e}")
        return None


def is_authenticated(authorization: Optional[str] = Header(None)):
    """
    Extract user from Bearer token.
    Return None if token is missing or invalid.
    """
    if not authorization:
        return None  # No token means offline or guest user

    # Expect format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": True},  # verifies expiration
        )
        user = payload.get("user")
        return user
    except JWTError:
        return None


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


def require_admin(
    user: dict = Depends(require_signin),
):
    try:
        if user.get("role") is None or user.get("is_root") is None:
            api_response(
                status.HTTP_401_UNAUTHORIZED,
                "Access denied: no role found",
            )
        role = user.get("role")
        user_permissions = role.get("permissions", [])
        if (
            role.get("title") != "root"
            and user.get("is_root") is False
            and "system:*" not in user_permissions
        ):
            api_response(
                status.HTTP_403_FORBIDDEN,
                "Access denied: Admins only",
            )

        return user  # user info with "email", "id", "role"

    except JWTError:
        api_response(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
        )


def require_permission(*permissions: str):
    def permission_checker(
        user: dict = Depends(require_signin),
    ):

        role = user.get("role")

        if not role:
            api_response(403, "Permission denied")

        user_permissions = role.get("permissions", [])
        # Allow all if "all" is in permissions
        if "system:*" in user_permissions:
            return user

        # Allow if any of the required permissions is present
        if any(p in user_permissions for p in permissions):
            return user
        else:
            api_response(403, "Permission denied")

    return permission_checker
