from fastapi import Depends, HTTPException, Request
from jose import JWTError

from backend.auth.security import decode_token
from backend.Database import Permission, Role, RolePermission, SessionLocal, User, UserRole


# ── Base auth ──────────────────────────────────────────────────────────────────

def get_current_user(request: Request) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        session.expunge(user)
        return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Allows admin and moderator into the admin panel."""
    if user.role not in ("admin", "moderator"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Permission check ───────────────────────────────────────────────────────────

def _get_user_permission_codes(user_id: str) -> set[str]:
    """Load all permission codes the user has via their assigned roles."""
    with SessionLocal() as session:
        codes = (
            session.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .filter(UserRole.user_id == user_id)
            .all()
        )
        return {row[0] for row in codes}


def require_permission(permission_code: str):
    """
    Factory that returns a FastAPI dependency.

    Usage:
        @router.get("/something")
        def endpoint(user = Depends(require_permission("users.read"))):
            ...

    Admins (role == "admin") bypass permission checks automatically.
    Moderators are checked against their assigned RBAC permissions.
    """
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role == "admin":
            return user  # admins always pass

        codes = _get_user_permission_codes(str(user.id))
        if permission_code not in codes:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission_code}' required",
            )
        return user

    return _check
