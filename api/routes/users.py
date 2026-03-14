"""
Users routes — profile and stats.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException

from api.deps import get_current_user_id
from api.models import User, UserStats
from database import get_user_by_id, get_user_stats

router = APIRouter()


@router.get("/me", response_model=User)
async def get_me(access_token: Optional[str] = Cookie(None)):
    """Return current user's profile."""
    user_id = get_current_user_id(access_token)
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/stats", response_model=UserStats)
async def get_my_stats(access_token: Optional[str] = Cookie(None)):
    """Return document usage stats for current user."""
    user_id = get_current_user_id(access_token)
    return get_user_stats(user_id)
