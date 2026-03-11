from backend.Database import SessionLocal, Role, Permission, RolePermission

# ── Define all permissions ─────────────────────────────────────────────────────
# Format: (code, description)

ALL_PERMISSIONS = [
    # Dashboard
    ("dashboard.view",           "View the admin dashboard"),

    # Users
    ("users.read",               "View users list and details"),
    ("users.create",             "Create new users"),
    ("users.edit",               "Edit existing users"),
    ("users.delete",             "Delete users"),
    ("users.assign_roles",       "Assign roles to users"),

    # STT Logs
    ("logs.read",                "View STT logs list and details"),
    ("logs.delete",              "Delete STT log entries"),

    # Roles
    ("roles.read",               "View roles list"),
    ("roles.create",             "Create new roles"),
    ("roles.edit",               "Edit existing roles"),
    ("roles.delete",             "Delete roles"),
    ("roles.assign_permissions", "Assign permissions to roles"),

    # Permissions
    ("permissions.read",         "View permissions list"),
    ("permissions.create",       "Create new permissions"),
    ("permissions.edit",         "Edit existing permissions"),
    ("permissions.delete",       "Delete permissions"),

    # Transcriptions
    ("transcriptions.create",    "Use the STT model to transcribe audio files"),
]

# ── Define roles and which permissions they get ────────────────────────────────

ROLES = {
    "admin": [p[0] for p in ALL_PERMISSIONS],  # everything

    "moderator": [
        "dashboard.view",
        "users.read",
        "logs.read",
        "roles.read",
        "permissions.read",
        "transcriptions.create",
    ],

    "user": [
        "transcriptions.create",  # can use the STT app
    ],
}


# ── Seed function ──────────────────────────────────────────────────────────────

def seed_rbac():
    with SessionLocal() as session:

        # 1. Upsert all permissions
        perm_map: dict[str, str] = {}  # code -> id

        for code, description in ALL_PERMISSIONS:
            existing = session.query(Permission).filter_by(code=code).first()
            if existing:
                perm_map[code] = existing.id
            else:
                import uuid
                perm = Permission(
                    id=str(uuid.uuid4()),
                    code=code,
                    description=description,
                )
                session.add(perm)
                session.flush()
                perm_map[code] = perm.id

        # 2. Upsert all roles + assign permissions
        for role_name, perm_codes in ROLES.items():
            role = session.query(Role).filter_by(name=role_name).first()
            if not role:
                import uuid
                role = Role(id=str(uuid.uuid4()), name=role_name)
                session.add(role)
                session.flush()

            # Full replace: wipe existing assignments then re-insert
            session.query(RolePermission).filter_by(role_id=role.id).delete()

            for code in perm_codes:
                pid = perm_map.get(code)
                if pid:
                    session.add(RolePermission(role_id=role.id, permission_id=pid))

        session.commit()
        print("[seed_rbac] Roles and permissions seeded successfully.")


if __name__ == "__main__":
    seed_rbac()
