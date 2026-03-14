"""
Internal API — used by the Telegram bot to save documents.
Protected by INTERNAL_API_TOKEN (shared secret).
"""

import os
from fastapi import APIRouter, Header, HTTPException

from api.models import BotSaveRequest, BotSaveResponse
from database import get_or_create_user, create_document

router = APIRouter()

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
WEB_URL = os.getenv("WEB_URL", "")


@router.post("/bot/save", response_model=BotSaveResponse)
async def bot_save_document(
    body: BotSaveRequest,
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
):
    """
    Save a document created by the bot.
    Called by bot_v2.py after text processing.
    """
    if not INTERNAL_API_TOKEN or x_internal_token != INTERNAL_API_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    user_id = get_or_create_user(
        telegram_id=body.telegram_id,
        first_name=body.first_name,
        last_name=body.last_name,
        username=body.username,
    )

    doc_id = create_document(
        user_id=user_id,
        content=body.content,
        mode=body.mode,
        title=body.title,
        source="bot",
    )

    url = f"{WEB_URL}/documents/{doc_id}" if WEB_URL else ""
    return BotSaveResponse(document_id=doc_id, url=url)
