from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ── Permissions ────────────────────────────────────────────────────────────────

class PermissionOut(BaseModel):
    id: str
    code: str
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    code: str
    description: Optional[str] = None


class PermissionUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None


# ── Roles ──────────────────────────────────────────────────────────────────────

class RoleOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    permissions: list[PermissionOut] = []

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str


class RoleUpdate(BaseModel):
    name: Optional[str] = None


class AssignPermissionsBody(BaseModel):
    permission_ids: list[str]


# ── User roles ─────────────────────────────────────────────────────────────────

class AssignRolesBody(BaseModel):
    role_ids: list[str]
