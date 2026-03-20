"""
Folders routes — CRUD for user document folders.
"""

from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException

from api.deps import get_current_user_id
from api.models import Folder, FolderCreate, FolderRename
from database import (
    get_user_folders,
    create_folder,
    rename_folder,
    delete_folder,
)

router = APIRouter()


@router.get("", response_model=list[Folder])
async def list_folders(
    access_token: Optional[str] = Cookie(None),
):
    """Return all folders for the current user (flat list, build tree on client)."""
    user_id = get_current_user_id(access_token)
    return get_user_folders(user_id=user_id)


@router.post("", response_model=Folder, status_code=201)
async def create_folder_route(
    body: FolderCreate,
    access_token: Optional[str] = Cookie(None),
):
    """Create a new folder."""
    user_id = get_current_user_id(access_token)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Folder name cannot be empty")
    folder = create_folder(user_id=user_id, name=name, parent_id=body.parent_id)
    return folder


@router.put("/{folder_id}", response_model=Folder)
async def rename_folder_route(
    folder_id: int,
    body: FolderRename,
    access_token: Optional[str] = Cookie(None),
):
    """Rename a folder."""
    user_id = get_current_user_id(access_token)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Folder name cannot be empty")
    ok = rename_folder(folder_id=folder_id, user_id=user_id, name=name)
    if not ok:
        raise HTTPException(status_code=404, detail="Folder not found")
    folders = get_user_folders(user_id=user_id)
    folder = next((f for f in folders if f["id"] == folder_id), None)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


@router.delete("/{folder_id}")
async def delete_folder_route(
    folder_id: int,
    access_token: Optional[str] = Cookie(None),
):
    """Delete a folder and all its descendants. Moves their documents to Новые."""
    user_id = get_current_user_id(access_token)
    ok = delete_folder(folder_id=folder_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"ok": True}
