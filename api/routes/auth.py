"""
Auth routes — Telegram Login Widget verification, JWT issuance.
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Response
from jose import jwt

from api.deps import SECRET_KEY, ALGORITHM, get_current_user_id
from api.models import AuthRequest, AuthResponse, User
from database import get_or_create_user, get_user_by_id

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
JWT_EXPIRE_DAYS = 7


def _verify_telegram_hash(data: dict, bot_token: str) -> bool:
    """
    Verify Telegram Login Widget data integrity.
    Algorithm: https://core.telegram.org/widgets/login#checking-authorization
    """
    check_hash = data.get("hash")
    if not check_hash:
        return False

    # Build data-check-string from all fields except hash, sorted alphabetically
    fields = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))

    # Secret key = SHA-256 of the bot token
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, check_hash)


def _create_jwt(user_id: int) -> str:
    """Create JWT token valid for JWT_EXPIRE_DAYS days."""
    expires = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/telegram", response_model=AuthResponse)
async def auth_telegram(data: AuthRequest, response: Response):
    """
    Verify Telegram Login Widget callback data, create/update user, set JWT cookie.
    auth_date must be no older than 24 hours.
    """
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Bot token not configured")

    # Check auth_date freshness (24 hours)
    if time.time() - data.auth_date > 86400:
        raise HTTPException(status_code=401, detail="Auth data expired")

    # Verify hash
    data_dict = data.model_dump()
    if not _verify_telegram_hash(data_dict, TELEGRAM_BOT_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    # Create or update user
    user_id = get_or_create_user(
        telegram_id=data.id,
        first_name=data.first_name,
        last_name=data.last_name,
        username=data.username,
        photo_url=data.photo_url,
    )

    user = get_user_by_id(user_id)

    # Set JWT as httpOnly cookie
    token = _create_jwt(user_id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=JWT_EXPIRE_DAYS * 86400,
        path="/",
    )

    return AuthResponse(user=User(**user))


@router.get("/verify", response_model=AuthResponse)
async def verify_token(access_token: Optional[str] = Cookie(None)):
    """Check if the current token is valid. Returns user info."""
    user_id = get_current_user_id(access_token)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return AuthResponse(user=User(**user))


@router.post("/logout")
async def logout(response: Response):
    """Clear auth cookie."""
    response.delete_cookie(key="access_token", path="/")
    return {"ok": True}
