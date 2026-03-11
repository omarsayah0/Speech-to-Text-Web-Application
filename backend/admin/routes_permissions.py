from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.Database import Permission, SessionLocal, User
from backend.admin.schemas_rbac import PermissionCreate, PermissionOut, PermissionUpdate
from backend.auth.deps import require_permission
from backend.audit import save_audit_log  # ← new

router = APIRouter(prefix="/admin/permissions", tags=["admin-permissions"])


@router.get("", response_model=list[PermissionOut])
def list_permissions(_: User = Depends(require_permission("permissions.read"))):
    with SessionLocal() as session:
        rows = session.query(Permission).order_by(Permission.code).all()
        return [PermissionOut.model_validate(r) for r in rows]


@router.post("", response_model=PermissionOut, status_code=201)
def create_permission(body: PermissionCreate, admin: User = Depends(require_permission("permissions.create"))):
    with SessionLocal() as session:
        if session.query(Permission).filter_by(code=body.code).first():
            raise HTTPException(400, f"Permission '{body.code}' already exists")
        perm = Permission(id=str(uuid4()), code=body.code, description=body.description)
        session.add(perm)
        session.commit()
        session.refresh(perm)
        result = PermissionOut.model_validate(perm)

    save_audit_log(admin.email, "create_permission", f"Created permission '{body.code}'")  # ← audit
    return result


@router.patch("/{perm_id}", response_model=PermissionOut)
def update_permission(perm_id: str, body: PermissionUpdate, admin: User = Depends(require_permission("permissions.edit"))):
    with SessionLocal() as session:
        perm = session.get(Permission, perm_id)
        if not perm:
            raise HTTPException(404, "Permission not found")
        old_code = perm.code
        if body.code is not None:
            conflict = session.query(Permission).filter(
                Permission.code == body.code, Permission.id != perm_id
            ).first()
            if conflict:
                raise HTTPException(400, f"Code '{body.code}' already in use")
            perm.code = body.code
        if body.description is not None:
            perm.description = body.description
        session.commit()
        session.refresh(perm)
        result = PermissionOut.model_validate(perm)

    save_audit_log(admin.email, "update_permission", f"Updated permission '{old_code}' → '{perm.code}'")  # ← audit
    return result


@router.delete("/{perm_id}", status_code=204)
def delete_permission(perm_id: str, admin: User = Depends(require_permission("permissions.delete"))):
    with SessionLocal() as session:
        perm = session.get(Permission, perm_id)
        if not perm:
            raise HTTPException(404, "Permission not found")
        perm_code = perm.code
        session.delete(perm)
        session.commit()

    save_audit_log(admin.email, "delete_permission", f"Deleted permission '{perm_code}'")  # ← audit
