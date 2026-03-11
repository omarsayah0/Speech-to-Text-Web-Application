from fastapi import APIRouter, Depends

from backend.Database import STTLog, SessionLocal
from backend.auth.deps import get_current_user, require_admin

router = APIRouter()


@router.get("/logs")
def all_logs(admin=Depends(require_admin)):
    with SessionLocal() as session:
        rows = (
            session.query(STTLog)
            .order_by(STTLog.created_at.desc())
            .limit(200)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "user_id": r.user_id,
                "filename": r.original_filename,
                "model": r.model,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "processing_time_ms": r.processing_time_ms,
                "file_size_bytes": r.file_size_bytes,
                "transcript_length": r.transcript_length,
                "client_ip": r.client_ip,
                "error_message": r.error_message,
            }
            for r in rows
        ]


@router.get("/logs/me")
def my_logs(current_user=Depends(get_current_user)):
    with SessionLocal() as session:
        rows = (
            session.query(STTLog)
            .filter_by(user_id=str(current_user.id))
            .order_by(STTLog.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "filename": r.original_filename,
                "model": r.model,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "processing_time_ms": r.processing_time_ms,
                "transcript_length": r.transcript_length,
            }
            for r in rows
        ]
