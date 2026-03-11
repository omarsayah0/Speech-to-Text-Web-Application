import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from backend.Database import STTLog, SessionLocal, log_transcription
from backend.auth.deps import get_current_user
from backend.service import DEFAULT_MODEL, SUPPORTED_MODELS, transcribe_file
from backend.plans import can_use_model, normalize_plan
from backend.audit import save_audit_log  # ← new

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}


@router.post("/transcriptions")
async def create_transcription(
    request: Request,
    file: UploadFile = File(...),
    model: str = Query(default=DEFAULT_MODEL, description=f"One of: {SUPPORTED_MODELS}"),
    current_user=Depends(get_current_user),
):
    client_ip = request.client.host if request.client else None

    if not file.filename:
        raise HTTPException(400, "Missing filename")

    if model not in SUPPORTED_MODELS:
        raise HTTPException(400, f"Unsupported model '{model}'. Choose from {SUPPORTED_MODELS}")

    # Enforce plan-based model access
    user_plan = normalize_plan(getattr(current_user, "plan", "tiny"))
    if not can_use_model(user_plan, model):
        raise HTTPException(
            403,
            f"Your current plan ({user_plan}) does not include the '{model}' model. "
            f"Please upgrade your plan."
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    job_id = str(uuid4())
    dst_path = UPLOAD_DIR / f"{job_id}{ext}"
    dst_path.write_bytes(content)

    file_size = len(content)
    start = time.monotonic()

    try:
        result = transcribe_file(dst_path, model_name=model)
    except Exception as exc:
        processing_time_ms = int((time.monotonic() - start) * 1000)
        log_transcription(
            original_filename=file.filename,
            stored_filename=dst_path.name,
            file_size_bytes=file_size,
            model=model,
            status="failed",
            processing_time_ms=processing_time_ms,
            client_ip=client_ip,
            error_message=str(exc),
            user_id=str(current_user.id),
        )
        save_audit_log(current_user.email, "transcription_failed", f"File '{file.filename}' model={model} error={exc}")  # ← audit
        raise HTTPException(500, f"Transcription failed: {exc}") from exc

    processing_time_ms = int((time.monotonic() - start) * 1000)
    transcript = result.get("text", "")

    log_transcription(
        original_filename=file.filename,
        stored_filename=dst_path.name,
        file_size_bytes=file_size,
        model=model,
        status="success",
        processing_time_ms=processing_time_ms,
        transcript_length=len(transcript),
        client_ip=client_ip,
        full_text=transcript,
        user_id=str(current_user.id),
    )
    save_audit_log(current_user.email, "transcription", f"Transcribed '{file.filename}' model={model} ({processing_time_ms}ms)")  # ← audit

    return {
        "id": job_id,
        "filename": file.filename,
        "stored_as": dst_path.name,
        **result,
    }


@router.get("/transcriptions/me")
def my_transcriptions(current_user=Depends(get_current_user)):
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
                "transcript_length": r.transcript_length,
                "processing_time_ms": r.processing_time_ms,
            }
            for r in rows
        ]
