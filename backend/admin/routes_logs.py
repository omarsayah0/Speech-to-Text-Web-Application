from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.Database import STTLog, SessionLocal, User
from backend.admin.schemas import LogListResponse, LogOut
from backend.auth.deps import require_admin

router = APIRouter(prefix="/admin/stt-logs", tags=["admin-logs"])


def _log_to_out(r: STTLog) -> LogOut:
    return LogOut(
        id=str(r.id),
        created_at=r.created_at,
        original_filename=r.original_filename,
        stored_filename=r.stored_filename,
        file_size_bytes=r.file_size_bytes,
        model=r.model,
        status=r.status,
        processing_time_ms=r.processing_time_ms,
        transcript_length=r.transcript_length,
        client_ip=r.client_ip,
        error_message=r.error_message,
        extra=r.extra,
        user_id=r.user_id,
    )


@router.get("", response_model=LogListResponse)
def list_logs(
    limit: int = 20,
    offset: int = 0,
    q: str = "",
    status: str = "",
    model: str = "",
    user_id: str = "",
    _admin: User = Depends(require_admin),
):
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
        items = [_log_to_out(r) for r in rows]

    return LogListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{log_id}", response_model=LogOut)
def get_log(log_id: str, _admin: User = Depends(require_admin)):
    try:
        uid = UUID(log_id)
    except ValueError:
        raise HTTPException(400, "Invalid log ID format")

    with SessionLocal() as session:
        row = session.get(STTLog, uid)
        if not row:
            raise HTTPException(404, "Log not found")
        return _log_to_out(row)


@router.delete("/{log_id}", status_code=204)
def delete_log(log_id: str, _admin: User = Depends(require_admin)):
    try:
        uid = UUID(log_id)
    except ValueError:
        raise HTTPException(400, "Invalid log ID format")

    with SessionLocal() as session:
        row = session.get(STTLog, uid)
        if not row:
            raise HTTPException(404, "Log not found")
        session.delete(row)
        session.commit()
