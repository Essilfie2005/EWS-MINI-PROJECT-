"""
Auth router – login and registration endpoints for the EWS dashboard.

Supports both database-backed users (registered via /register) and the
legacy hard-coded admin/counsellor accounts for backward compatibility.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.database import get_db
from app.models.db_models import AppUser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ── Legacy hard-coded users (backward compatibility) ──────────────────────────
_LEGACY_USERS = {
    "admin":      {"password": "ews2024", "role": "admin"},
    "counsellor": {"password": "ews2024", "role": "counsellor"},
}


# ── Schemas ───────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    role: str = "counsellor"
    email: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"admin", "counsellor"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(allowed)}")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 64:
            raise ValueError("Username must be 64 characters or fewer")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class RegisterResponse(BaseModel):
    message: str
    username: str
    role: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a dashboard user.
    Checks DB users first, then falls back to legacy hard-coded accounts.
    Returns a base64 token on success.
    """
    username = body.username.strip()
    password = body.password

    # 1. Check database users
    result = await db.execute(select(AppUser).where(AppUser.username == username))
    db_user = result.scalar_one_or_none()

    if db_user:
        if not db_user.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")
        if not verify_password(password, db_user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        role = db_user.role
    else:
        # 2. Fall back to legacy hard-coded accounts
        legacy = _LEGACY_USERS.get(username)
        if not legacy or legacy["password"] != password:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        role = legacy["role"]

    raw = f"{username}:{password}"
    token = base64.b64encode(raw.encode()).decode()
    logger.info("User '%s' logged in successfully (role=%s)", username, role)
    return LoginResponse(token=token, username=username, role=role)


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new dashboard user account.
    Passwords are hashed with bcrypt before storage.
    """
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    username = body.username.strip()

    # Check username not taken (db or legacy)
    existing = await db.execute(select(AppUser).where(AppUser.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    if username in _LEGACY_USERS:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Check email uniqueness if provided
    if body.email:
        email_check = await db.execute(select(AppUser).where(AppUser.email == body.email))
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")

    user = AppUser(
        username=username,
        email=body.email or None,
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    logger.info("New user registered: '%s' (role=%s)", username, body.role)
    return RegisterResponse(
        message="Account created successfully. You can now log in.",
        username=username,
        role=body.role,
    )


@router.post("/logout")
async def logout():
    """Client-side logout – token invalidation is handled in the frontend."""
    return {"message": "Logged out successfully"}
