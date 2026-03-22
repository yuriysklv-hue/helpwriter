"""
Documents routes — CRUD for user documents.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException, Query

from api.deps import get_current_user_id
from api.models import Document, DocumentCreate, DocumentsResponse, DocumentUpdate, MoveDocument
from database import (
    create_document,
    get_document_by_id,
    get_user_documents,
    update_document,
    delete_document,
    move_document_to_folder,
)

router = APIRouter()


@router.post("", response_model=Document, status_code=201)
async def create_doc(
    body: DocumentCreate,
    access_token: Optional[str] = Cookie(None),
):
    """Create a new empty document from the web editor."""
    user_id = get_current_user_id(access_token)
    doc_id = create_document(
        user_id=user_id,
        content=body.content or "",
        mode=body.mode or "transcription",
        title=body.title or None,
        source="web",
        folder_id=body.folder_id,
    )
    doc = get_document_by_id(doc_id=doc_id, user_id=user_id)
    return doc


@router.get("", response_model=DocumentsResponse)
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mode: Optional[str] = Query(None),
    view: Optional[str] = Query(None),       # 'inbox' → folder_id IS NULL (Новые)
    folder_id: Optional[int] = Query(None),  # specific folder ID
    access_token: Optional[str] = Cookie(None),
):
    """Return paginated list of user's documents.

    - view=inbox   → documents in Новые (no folder assigned)
    - folder_id=N  → documents in folder N
    - (default)    → all documents
    """
    user_id = get_current_user_id(access_token)
    result = get_user_documents(
        user_id=user_id, limit=limit, offset=offset,
        mode=mode, view=view, folder_id=folder_id,
    )
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


@router.put("/{doc_id}/move", response_model=Document)
async def move_document(
    doc_id: int,
    body: MoveDocument,
    access_token: Optional[str] = Cookie(None),
):
    """Move document to a folder. folder_id=null moves to Новые."""
    user_id = get_current_user_id(access_token)
    ok = move_document_to_folder(doc_id=doc_id, user_id=user_id, folder_id=body.folder_id)
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
