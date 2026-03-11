from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.Database import Permission, Role, RolePermission, SessionLocal, User, UserRole
from backend.admin.schemas_rbac import (
    AssignPermissionsBody, AssignRolesBody,
    PermissionOut, RoleCreate, RoleOut, RoleUpdate,
)
from backend.auth.deps import require_permission
from backend.audit import save_audit_log  # ← new

router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])


def _load_role(session, role_id: str) -> Role:
    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    return role


def _role_to_out(session, role: Role) -> RoleOut:
    perms = (
        session.query(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role.id)
        .all()
    )
    return RoleOut(
        id=role.id,
        name=role.name,
        created_at=role.created_at,
        permissions=[PermissionOut.model_validate(p) for p in perms],
    )


@router.get("", response_model=list[RoleOut])
def list_roles(_: User = Depends(require_permission("roles.read"))):
    with SessionLocal() as session:
        roles = session.query(Role).order_by(Role.name).all()
        return [_role_to_out(session, r) for r in roles]


@router.get("/{role_id}", response_model=RoleOut)
def get_role(role_id: str, _: User = Depends(require_permission("roles.read"))):
    with SessionLocal() as session:
        role = _load_role(session, role_id)
        return _role_to_out(session, role)


@router.post("", response_model=RoleOut, status_code=201)
def create_role(body: RoleCreate, admin: User = Depends(require_permission("roles.create"))):
    with SessionLocal() as session:
        if session.query(Role).filter_by(name=body.name).first():
            raise HTTPException(400, f"Role '{body.name}' already exists")
        role = Role(id=str(uuid4()), name=body.name)
        session.add(role)
        session.commit()
        session.refresh(role)
        result = _role_to_out(session, role)

    save_audit_log(admin.email, "create_role", f"Created role '{body.name}'")  # ← audit
    return result


@router.patch("/{role_id}", response_model=RoleOut)
def update_role(role_id: str, body: RoleUpdate, admin: User = Depends(require_permission("roles.edit"))):
    with SessionLocal() as session:
        role = _load_role(session, role_id)
        old_name = role.name
        if body.name is not None:
            conflict = session.query(Role).filter(Role.name == body.name, Role.id != role_id).first()
            if conflict:
                raise HTTPException(400, f"Role '{body.name}' already exists")
            role.name = body.name
        session.commit()
        session.refresh(role)
        result = _role_to_out(session, role)

    save_audit_log(admin.email, "update_role", f"Renamed role '{old_name}' → '{role.name}'")  # ← audit
    return result


@router.delete("/{role_id}", status_code=204)
def delete_role(role_id: str, admin: User = Depends(require_permission("roles.delete"))):
    with SessionLocal() as session:
        role = _load_role(session, role_id)
        role_name = role.name
        session.delete(role)
        session.commit()

    save_audit_log(admin.email, "delete_role", f"Deleted role '{role_name}'")  # ← audit


@router.put("/{role_id}/permissions", response_model=RoleOut)
def assign_permissions(role_id: str, body: AssignPermissionsBody, admin: User = Depends(require_permission("roles.assign_permissions"))):
    with SessionLocal() as session:
        role = _load_role(session, role_id)
        for pid in body.permission_ids:
            if not session.get(Permission, pid):
                raise HTTPException(404, f"Permission '{pid}' not found")
        session.query(RolePermission).filter_by(role_id=role_id).delete()
        for pid in body.permission_ids:
            session.add(RolePermission(role_id=role_id, permission_id=pid))
        session.commit()
        result = _role_to_out(session, role)

    save_audit_log(admin.email, "assign_permissions", f"Assigned {len(body.permission_ids)} permission(s) to role '{role.name}'")  # ← audit
    return result


# ── Assign roles to a user ─────────────────────────────────────────────────────

user_router = APIRouter(prefix="/admin/users", tags=["admin-user-roles"])


@user_router.put("/{user_id}/roles")
def assign_user_roles(user_id: str, body: AssignRolesBody, admin: User = Depends(require_permission("users.assign_roles"))):
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(404, "User not found")
        for rid in body.role_ids:
            if not session.get(Role, rid):
                raise HTTPException(404, f"Role '{rid}' not found")
        session.query(UserRole).filter_by(user_id=user_id).delete()
        for rid in body.role_ids:
            session.add(UserRole(user_id=user_id, role_id=rid))
        session.commit()
        roles = (
            session.query(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user_id)
            .all()
        )
        role_names = [r.name for r in roles]
        target_email = user.email

    save_audit_log(admin.email, "assign_user_roles", f"Assigned roles {role_names} to user {target_email}")  # ← audit
    return {"user_id": user_id, "roles": [{"id": r.id, "name": r.name} for r in roles]}
