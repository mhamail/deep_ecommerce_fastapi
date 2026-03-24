# My way to code Fastapi Doc Ai For Operation,Security Func, Media etc

## in this project we use latest fastapi method, uv package manager, sql model for schemas

## Operations

//=========================================

## Update Operation

// =======================================

```
from src.api.core.operation import listRecords, updateOp
```

```py
# Update only the fields that are provided in the request
# customFields = ["phone", "firstname", "lastname", "email"]
def updateOp(
    instance,
    request,
    session,
    customFields=None,
):
    if customFields:
        for field in customFields:
            if hasattr(request, field):
                value = getattr(request, field)
                if value is not None:
                    setattr(instance, field, value)
    else:
        data = request.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(instance, key, value)
    if hasattr(instance, "updated_at"):
        instance.updated_at = datetime.now(timezone.utc)
    session.add(instance)

    return instance

```

//=========================================

## Security

// =======================================

```py
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select
from sqlmodel import Session
from fastapi import (
    Depends,
    Header,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from src.api.core.response import api_response
from src.api.models import User

ALGORITHM = "HS256"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


## get user
def exist_user(db: Session, email: str):
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
            expires or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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


def require_admin(user: dict = Depends(require_signin)):
    roles: List[str] = user.get("roles", [])
    if "root" not in roles:
        api_response(status.HTTP_403_FORBIDDEN, "Root User only")
    return user


def require_permission(*permissions: str):
    def permission_checker(user: dict = Depends(require_signin)):
        user_permissions: List[str] = user.get("permissions", [])

        # ✅ system:* always passes
        if "system:*" in user_permissions:
            return user

        # ✅ OR logic: check if user has any required permission
        if any(p in user_permissions for p in permissions):
            return user

        # ❌ no match → deny
        api_response(status.HTTP_403_FORBIDDEN, "Permission denied")

    return permission_checker

```
