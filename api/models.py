"""
Pydantic models for HelpWriter API.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class User(BaseModel):
    id: int
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: str
    last_login_at: str


class Document(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    content: str
    mode: str
    source: str
    created_at: str
    updated_at: str
    folder_id: Optional[int] = None


class DocumentListItem(BaseModel):
    id: int
    title: Optional[str] = None
    preview: str
    mode: str
    source: str
    created_at: str
    updated_at: str
    folder_id: Optional[int] = None


class DocumentsResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    limit: int
    offset: int


class DocumentCreate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    mode: Optional[str] = None
    folder_id: Optional[int] = None


class DocumentUpdate(BaseModel):
    content: Optional[str] = None
    title: Optional[str] = None


class MoveDocument(BaseModel):
    folder_id: Optional[int] = None  # None = move to Новые


class Folder(BaseModel):
    id: int
    user_id: int
    parent_id: Optional[int] = None
    name: str
    created_at: str


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class FolderRename(BaseModel):
    name: str


class AuthRequest(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class AuthResponse(BaseModel):
    user: User


class UserStats(BaseModel):
    total_documents: int
    transcription: int
    structure: int
    ideas: int


# Internal API (bot → API)
class BotSaveRequest(BaseModel):
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    content: str
    mode: str
    title: Optional[str] = None


class BotSaveResponse(BaseModel):
    document_id: int
    url: str
