"""JWT authentication routes for RBAC — staff vs manager roles."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.hash import bcrypt
from pydantic import BaseModel

from ..core.config import settings
from ..services.repositories import repository

auth_router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8

# Local/demo users. Production must authenticate against MongoDB users.
DEMO_USERS = {
    "staff1": {"password": "staff123", "role": "staff", "name": "Priya Sharma", "branch": "Central District", "desk_id": "FD-01"},
    "staff2": {"password": "staff123", "role": "staff", "name": "Rohan Mehta", "branch": "Central District", "desk_id": "FD-02"},
    "staff3": {"password": "staff123", "role": "staff", "name": "Neha Iyer", "branch": "Central District", "desk_id": "FD-03"},
    "staff4": {"password": "staff123", "role": "staff", "name": "Amit Kulkarni", "branch": "Central District", "desk_id": "FD-04"},
    "staff5": {"password": "staff123", "role": "staff", "name": "Farah Khan", "branch": "Central District", "desk_id": "FD-05"},
    "manager1": {"password": "manager123", "role": "manager", "name": "Anil Deshmukh", "branch": "Central District"},
}


def _verify_password(plain: str, stored: str) -> bool:
    """Compare password — supports both bcrypt hashes and plain-text demo passwords."""
    if stored.startswith("$2b$") or stored.startswith("$2a$"):
        return bcrypt.verify(plain, stored)
    return plain == stored


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    name: str
    branch: str
    username: str
    deskId: str | None = None


class UserInfo(BaseModel):
    username: str
    role: str
    name: str
    branch: str
    deskId: str | None = None


@auth_router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    db_user = await repository.get_user(body.username)
    canonical_username = body.username
    if db_user is not None:
        user = db_user
        canonical_username = user.get("username", body.username)
    elif settings.seed_demo_users or settings.seed_demo_data:
        user = DEMO_USERS.get(body.username)
        if user is None:
            employee_aliases = {
                "104851": "staff1",
                "104852": "staff2",
                "104853": "staff3",
                "104854": "staff4",
                "104855": "staff5",
                "200100": "manager1",
            }
            canonical_username = employee_aliases.get(body.username, body.username)
            user = DEMO_USERS.get(canonical_username)
    else:
        user = None
    if not user or not _verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "sub": canonical_username,
        "role": user["role"],
        "name": user["name"],
        "branch": user["branch"],
        "deskId": user.get("desk_id") or user.get("deskId"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return LoginResponse(
        token=token,
        role=user["role"],
        name=user["name"],
        branch=user["branch"],
        username=canonical_username,
        deskId=user.get("desk_id") or user.get("deskId"),
    )


def decode_token_value(token: str | None) -> UserInfo:
    """Decode and validate a raw JWT string."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return UserInfo(
            username=payload["sub"],
            role=payload["role"],
            name=payload["name"],
            branch=payload["branch"],
            deskId=payload.get("deskId"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def decode_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> UserInfo:
    """Dependency to extract and verify JWT from Authorization header."""
    return decode_token_value(credentials.credentials if credentials else None)


def decode_token_header_or_query(
    token: str | None = Query(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserInfo:
    """Accept Bearer auth for REST and temporary query-token links for kiosk downloads."""
    return decode_token_value(credentials.credentials if credentials else token)


def require_role(role: str):
    """Dependency factory for role-based access control."""
    def checker(user: UserInfo = Depends(decode_token)):
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user
    return checker
