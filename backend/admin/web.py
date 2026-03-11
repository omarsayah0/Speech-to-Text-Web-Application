from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError

from backend.auth.security import decode_token
from backend.Database import (
    Permission, Role, RolePermission, SessionLocal,
    STTLog, User, UserRole
)

router = APIRouter(prefix="/admin", tags=["admin-web"])

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "admin"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _get_admin_or_redirect(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None, RedirectResponse(url="/login")
    try:
        payload = decode_token(token)
    except JWTError:
        return None, RedirectResponse(url="/login")
    user_id = payload.get("sub")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            return None, RedirectResponse(url="/login")
        # ← Role checked from DB, not from JWT payload
        if user.role not in ("admin", "moderator"):
            return None, RedirectResponse(url="/app")
        session.expunge(user)
    return user, None


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    with SessionLocal() as session:
        user_count = session.query(User).count()
        log_count = session.query(STTLog).count()
        failed_count = session.query(STTLog).filter_by(status="failed").count()
        role_count = session.query(Role).count()
        perm_count = session.query(Permission).count()

        roles_summary = []
        for r in session.query(Role).order_by(Role.name).all():
            perms = (
                session.query(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .filter(RolePermission.role_id == r.id)
                .order_by(Permission.code)
                .all()
            )
            codes = [p[0] for p in perms]
            roles_summary.append({"name": r.name, "perm_count": len(codes), "perm_codes": codes})

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "admin": user,
        "is_admin": user.role == "admin",
        "user_count": user_count, "log_count": log_count,
        "failed_count": failed_count, "role_count": role_count,
        "perm_count": perm_count, "roles_summary": roles_summary,
    })


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
def users_list(request: Request, q: str = "", limit: int = 20, offset: int = 0):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    with SessionLocal() as session:
        query = session.query(User)
        if q:
            query = query.filter(User.email.ilike(f"%{q}%"))
        total = query.count()
        rows = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        users = [{"id": r.id, "email": r.email, "role": r.role,"plan": r.plan, "created_at": r.created_at} for r in rows]
    return templates.TemplateResponse("users_list.html", {
        "request": request, "admin": user,
        "is_admin": user.role == "admin",
        "users": users, "total": total, "limit": limit, "offset": offset, "q": q,
        "prev_offset": max(0, offset - limit), "next_offset": offset + limit,
        "has_prev": offset > 0, "has_next": offset + limit < total,
    })


@router.get("/users/new", response_class=HTMLResponse)
def user_new_form(request: Request):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    if user.role != "admin":
        return RedirectResponse(url="/admin/users")
    with SessionLocal() as session:
        all_roles = session.query(Role).order_by(Role.name).all()
        all_roles_data = [{"id": r.id, "name": r.name} for r in all_roles]
    return templates.TemplateResponse("user_form.html", {
        "request": request, "admin": user,
        "is_admin": True,
        "edit_user": None, "assigned_role_ids": [],
        "all_roles": all_roles_data, "error": None,
    })


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def user_edit_form(user_id: str, request: Request):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    if user.role != "admin":
        return RedirectResponse(url="/admin/users")
    with SessionLocal() as session:
        target = session.get(User, user_id)
        if not target:
            return RedirectResponse(url="/admin/users")
        # ── CHANGE: include plan so the form can pre-select it ──
        edit_user = {"id": target.id, "email": target.email, "role": target.role, "plan": target.plan}
        assigned = session.query(UserRole).filter_by(user_id=user_id).all()
        assigned_role_ids = [ur.role_id for ur in assigned]
        all_roles = session.query(Role).order_by(Role.name).all()
        all_roles_data = [{"id": r.id, "name": r.name} for r in all_roles]
    return templates.TemplateResponse("user_form.html", {
        "request": request, "admin": user,
        "is_admin": True,
        "edit_user": edit_user, "assigned_role_ids": assigned_role_ids,
        "all_roles": all_roles_data, "error": None,
    })


# ── STT Logs ───────────────────────────────────────────────────────────────────

@router.get("/logs", response_class=HTMLResponse)
def logs_list(
    request: Request, q: str = "", status: str = "",
    model: str = "", user_id: str = "", limit: int = 20, offset: int = 0,
):
    admin_user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    with SessionLocal() as session:
        query = session.query(STTLog)
        if q:
            query = query.filter(STTLog.original_filename.ilike(f"%{q}%"))
        if status:
            query = query.filter(STTLog.status == status)
        if model:
            query = query.filter(STTLog.model == model)
        if user_id:
            query = query.filter(STTLog.user_id == user_id)
        total = query.count()
        rows = query.order_by(STTLog.created_at.desc()).offset(offset).limit(limit).all()
        logs = [{
            "id": str(r.id), "created_at": r.created_at,
            "original_filename": r.original_filename, "model": r.model,
            "status": r.status, "processing_time_ms": r.processing_time_ms,
            "file_size_bytes": r.file_size_bytes, "transcript_length": r.transcript_length,
            "user_id": r.user_id,
        } for r in rows]
    return templates.TemplateResponse("logs_list.html", {
        "request": request, "admin": admin_user,
        "is_admin": admin_user.role == "admin",
        "logs": logs, "total": total, "limit": limit, "offset": offset,
        "q": q, "status": status, "model": model, "user_id": user_id,
        "prev_offset": max(0, offset - limit), "next_offset": offset + limit,
        "has_prev": offset > 0, "has_next": offset + limit < total,
    })


@router.get("/logs/{log_id}", response_class=HTMLResponse)
def log_detail(log_id: str, request: Request):
    admin_user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    try:
        uid = UUID(log_id)
    except ValueError:
        return RedirectResponse(url="/admin/logs")
    with SessionLocal() as session:
        row = session.get(STTLog, uid)
        if not row:
            return RedirectResponse(url="/admin/logs")
        log = {
            "id": str(row.id), "created_at": row.created_at,
            "original_filename": row.original_filename, "stored_filename": row.stored_filename,
            "file_size_bytes": row.file_size_bytes, "model": row.model,
            "status": row.status, "processing_time_ms": row.processing_time_ms,
            "transcript_length": row.transcript_length, "client_ip": row.client_ip,
            "error_message": row.error_message, "extra": row.extra, "user_id": row.user_id,
        }
    return templates.TemplateResponse("log_detail.html", {
        "request": request, "admin": admin_user,
        "is_admin": admin_user.role == "admin",
        "log": log,
    })


# ── Permissions page ───────────────────────────────────────────────────────────

@router.get("/permissions", response_class=HTMLResponse)
def permissions_page(request: Request):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    with SessionLocal() as session:
        perms = session.query(Permission).order_by(Permission.code).all()
        data = [{"id": p.id, "code": p.code, "description": p.description, "created_at": p.created_at} for p in perms]
    return templates.TemplateResponse("permissions.html", {
        "request": request, "admin": user,
        "is_admin": user.role == "admin",
        "permissions": data,
    })


# ── Roles page ─────────────────────────────────────────────────────────────────

@router.get("/roles", response_class=HTMLResponse)
def roles_page(request: Request):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    with SessionLocal() as session:
        roles = session.query(Role).order_by(Role.name).all()
        roles_data = []
        for r in roles:
            assigned = session.query(RolePermission).filter_by(role_id=r.id).all()
            roles_data.append({
                "id": r.id, "name": r.name, "created_at": r.created_at,
                "permission_count": len(assigned),
            })
        all_perms = session.query(Permission).order_by(Permission.code).all()
        all_perms_data = [{"id": p.id, "code": p.code, "description": p.description} for p in all_perms]
    return templates.TemplateResponse("roles.html", {
        "request": request, "admin": user,
        "is_admin": user.role == "admin",
        "roles": roles_data, "all_permissions": all_perms_data,
    })


@router.get("/roles/{role_id}/edit", response_class=HTMLResponse)
def role_edit_page(role_id: str, request: Request):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir
    if user.role != "admin":
        return RedirectResponse(url="/admin/roles")
    with SessionLocal() as session:
        role = session.get(Role, role_id)
        if not role:
            return RedirectResponse(url="/admin/roles")
        assigned = session.query(RolePermission).filter_by(role_id=role_id).all()
        assigned_ids = [rp.permission_id for rp in assigned]
        all_perms = session.query(Permission).order_by(Permission.code).all()
        all_perms_data = [{"id": p.id, "code": p.code, "description": p.description} for p in all_perms]
        role_data = {"id": role.id, "name": role.name}
    return templates.TemplateResponse("role_edit.html", {
        "request": request, "admin": user,
        "is_admin": True,
        "role": role_data, "all_permissions": all_perms_data,
        "assigned_ids": assigned_ids,
    })

from backend.Database import AuditLog


@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(
    request: Request,
    q: str = "",
    action: str = "",
    limit: int = 50,
    offset: int = 0,
):
    user, redir = _get_admin_or_redirect(request)
    if redir:
        return redir

    with SessionLocal() as session:
        query = session.query(AuditLog)

        if q:
            query = query.filter(AuditLog.user_email.ilike(f"%{q}%"))

        if action:
            query = query.filter(AuditLog.action.ilike(f"%{action}%"))

        total = query.count()

        rows = (
            query.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        logs = [
            {
                "created_at": r.created_at,
                "user_email": r.user_email,
                "action": r.action,
                "details": r.details,
            }
            for r in rows
        ]

    return templates.TemplateResponse(
        "audit_logs.html",
        {
            "request": request,
            "admin": user,
            "is_admin": user.role == "admin",
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
            "q": q,
            "action": action,
            "prev_offset": max(0, offset - limit),
            "next_offset": offset + limit,
            "has_prev": offset > 0,
            "has_next": offset + limit < total,
        },
    )