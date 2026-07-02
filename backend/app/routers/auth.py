"""
Auth router – simple login endpoint for the EWS dashboard.

Credentials are hard-coded for this demo/mini-project system.
In a production deployment, replace with a proper user database and
bcrypt password hashing.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ── Hard-coded users (extend list for more counsellors) ───────────────────────
_USERS = {
    "admin":      {"password": "ews2024", "role": "admin"},
    "counsellor": {"password": "ews2024", "role": "counsellor"},
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """
    Authenticate a dashboard user.
    Returns a base64 token (suitable for the Bearer header) on success.
    """
    user = _USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Simple base64 token — adequate for a university LAN demo system
    raw = f"{body.username}:{body.password}"
    token = base64.b64encode(raw.encode()).decode()

    logger.info("User '%s' logged in successfully", body.username)
    return LoginResponse(token=token, username=body.username, role=user["role"])


@router.post("/logout")
async def logout():
    """Client-side logout — token invalidation is handled in the frontend."""
    return {"message": "Logged out successfully"}
