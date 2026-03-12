"""
Documents routes — CRUD for user documents.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query

from api.deps import get_current_user_id
from api.models import Document, DocumentsResponse, DocumentUpdate
from database import (
    get_document_by_id,
    get_user_documents,
    update_document,
    delete_document,
)

router = APIRouter()


@router.get("", response_model=DocumentsResponse)
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mode: Optional[str] = Query(None),
    access_token: Optional[str] = Cookie(None),
):
    """Return paginated list of user's documents."""
    user_id = get_current_user_id(access_token)
    result = get_user_documents(user_id=user_id, limit=limit, offset=offset, mode=mode)
    return result


@router.get("/{doc_id}", response_model=Document)
async def get_document(
    doc_id: int,
    access_token: Optional[str] = Cookie(None),
):
    """Return a single document by ID."""
    user_id = get_current_user_id(access_token)
    doc = get_document_by_id(doc_id=doc_id, user_id=user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{doc_id}", response_model=Document)
async def edit_document(
    doc_id: int,
    body: DocumentUpdate,
    access_token: Optional[str] = Cookie(None),
):
    """Update document content and/or title."""
    user_id = get_current_user_id(access_token)
    ok = update_document(
        doc_id=doc_id,
        user_id=user_id,
        content=body.content,
        title=body.title,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = get_document_by_id(doc_id=doc_id, user_id=user_id)
    return doc


@router.delete("/{doc_id}")
async def remove_document(
    doc_id: int,
    access_token: Optional[str] = Cookie(None),
):
    """Soft-delete a document."""
    user_id = get_current_user_id(access_token)
    ok = delete_document(doc_id=doc_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}
