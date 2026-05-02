"""JWT authentication routes for RBAC — staff vs manager roles."""

from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
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

# Demo users (in production → MongoDB users collection)
DEMO_USERS = {
    "staff1": {"password": "staff123", "role": "staff", "name": "Priya Sharma", "branch": "Central District"},
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


class UserInfo(BaseModel):
    username: str
    role: str
    name: str
    branch: str


@auth_router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    db_user = await repository.get_user(body.username)
    if db_user is not None:
        user = db_user
    else:
        user = DEMO_USERS.get(body.username)
    if not user or not _verify_password(body.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "sub": body.username,
        "role": user["role"],
        "name": user["name"],
        "branch": user["branch"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return LoginResponse(
        token=token,
        role=user["role"],
        name=user["name"],
        branch=user["branch"],
    )


def decode_token_value(token: str | None) -> UserInfo:
    """Decode and validate a raw JWT string."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    # ── Demo Bypass for Kiosk ──
    if token == "demo":
        return UserInfo(
            username="demo_user",
            role="staff",
            name="Demo User",
            branch="Demo Branch"
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return UserInfo(
            username=payload["sub"],
            role=payload["role"],
            name=payload["name"],
            branch=payload["branch"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def decode_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> UserInfo:
    """Dependency to extract and verify JWT from Authorization header."""
    return decode_token_value(credentials.credentials if credentials else None)


def require_role(role: str):
    """Dependency factory for role-based access control."""
    def checker(user: UserInfo = Depends(decode_token)):
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user
    return checker
