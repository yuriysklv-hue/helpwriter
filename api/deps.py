"""
Dependencies and middleware for HelpWriter API.
JWT verification via httpOnly cookie.
"""

import os
from typing import Optional
from fastapi import Cookie, HTTPException
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"


def get_current_user_id(access_token: Optional[str] = Cookie(None)) -> int:
    """
    Extract user_id from JWT stored in httpOnly cookie.
    Raises 401 if token is missing or invalid.
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
