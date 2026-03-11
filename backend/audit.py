from backend.Database import AuditLog, SessionLocal


def save_audit_log(
    user_email: str | None,
    action: str,
    details: str = "",
) -> None:
    """Insert one audit_logs row. Never raises — logging must not break app flow."""
    try:
        with SessionLocal() as session:
            entry = AuditLog(
                user_email=user_email,
                action=action,
                details=details,
            )
            session.add(entry)
            session.commit()
    except Exception:
        pass  # audit failure must never crash the caller
