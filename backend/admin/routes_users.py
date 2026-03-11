from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.Database import SessionLocal, User
from backend.admin.schemas import UserCreate, UserListResponse, UserOut, UserUpdate
from backend.auth.deps import require_admin, require_permission
from backend.auth.security import hash_password
from backend.plans import VALID_PLANS
from backend.audit import save_audit_log  # ← new

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

VALID_ROLES = ("user", "moderator", "admin")


@router.get("", response_model=UserListResponse)
def list_users(
    limit: int = 20,
    offset: int = 0,
    q: str = "",
    _: User = Depends(require_permission("users.read")),
):
    with SessionLocal() as session:
        query = session.query(User)
        if q:
            query = query.filter(User.email.ilike(f"%{q}%"))
        total = query.count()
        rows = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        items = [UserOut.model_validate(r) for r in rows]
    return UserListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, _: User = Depends(require_permission("users.read"))):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        return UserOut.model_validate(user)


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, admin: User = Depends(require_permission("users.create"))):
    with SessionLocal() as session:
        if session.query(User).filter_by(email=body.email).first():
            raise HTTPException(400, "Email already registered")
        if body.role not in VALID_ROLES:
            raise HTTPException(400, f"role must be one of: {', '.join(VALID_ROLES)}")
        if body.plan not in VALID_PLANS:
            raise HTTPException(400, f"plan must be one of: {', '.join(VALID_PLANS)}")
        user = User(
            id=str(uuid4()),
            email=body.email,
            password_hash=hash_password(body.password),
            role=body.role,
            plan=body.plan,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        result = UserOut.model_validate(user)

    save_audit_log(admin.email, "create_user", f"Created user {body.email} (role={body.role}, plan={body.plan})")  # ← audit
    return result


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, admin: User = Depends(require_permission("users.edit"))):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        changes = []
        if body.email is not None:
            existing = session.query(User).filter(User.email == body.email, User.id != user_id).first()
            if existing:
                raise HTTPException(400, "Email already in use")
            changes.append(f"email→{body.email}")
            user.email = body.email
        if body.role is not None:
            if body.role not in VALID_ROLES:
                raise HTTPException(400, f"role must be one of: {', '.join(VALID_ROLES)}")
            changes.append(f"role→{body.role}")
            user.role = body.role
        if body.plan is not None:
            if body.plan not in VALID_PLANS:
                raise HTTPException(400, f"plan must be one of: {', '.join(VALID_PLANS)}")
            changes.append(f"plan→{body.plan}")
            user.plan = body.plan
        if body.password is not None and body.password.strip():
            changes.append("password changed")
            user.password_hash = hash_password(body.password)
        target_email = user.email
        session.commit()
        session.refresh(user)
        result = UserOut.model_validate(user)

    save_audit_log(admin.email, "update_user", f"Updated user {target_email}: {', '.join(changes) or 'no changes'}")  # ← audit
    return result


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: str, admin: User = Depends(require_permission("users.delete"))):
    if user_id == admin.id:
        raise HTTPException(400, "Cannot delete yourself")
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        target_email = user.email
        session.delete(user)
        session.commit()

    save_audit_log(admin.email, "delete_user", f"Deleted user {target_email}")  # ← audit
