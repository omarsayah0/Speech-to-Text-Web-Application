from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


# ── Users ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    email: str
    role: str
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"
    plan: str = "free"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    plan: Optional[str] = None


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    limit: int
    offset: int


# ── STT Logs ───────────────────────────────────────────────────────────────────

class LogOut(BaseModel):
    id: str
    created_at: datetime
    original_filename: str
    stored_filename: str
    file_size_bytes: int
    model: str
    status: str
    processing_time_ms: int
    transcript_length: Optional[int] = None
    client_ip: Optional[str] = None
    error_message: Optional[str] = None
    extra: Optional[Any] = None
    user_id: Optional[str] = None

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[LogOut]
    total: int
    limit: int
    offset: int
