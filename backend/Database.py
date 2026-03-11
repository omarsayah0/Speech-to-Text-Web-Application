import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine, Column, Text, BigInteger, Integer,
    DateTime, Boolean, ForeignKey, PrimaryKeyConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stt")
STORE_FULL_TEXT = os.getenv("STORE_FULL_TEXT", "false").lower() == "true"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ── Existing tables ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, nullable=False, default="user")
    plan = Column(Text, nullable=False, default="free")
    pro_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class STTLog(Base):
    __tablename__ = "stt_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    original_filename = Column(Text, nullable=False)
    stored_filename = Column(Text, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    model = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    processing_time_ms = Column(Integer, nullable=False)
    transcript_length = Column(Integer, nullable=True)
    client_ip = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    extra = Column(JSONB, nullable=True)
    user_id = Column(Text, ForeignKey("users.id"), nullable=True)


# ── RBAC tables ────────────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(Text, unique=True, nullable=False)          # e.g. "users.read"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Text, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Text, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("role_id", "permission_id"),)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Text, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("user_id", "role_id"),)


# ── Audit log table ────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(Text, nullable=True)
    action = Column(Text, nullable=False)
    details = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


# ── DB init ────────────────────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE stt_logs ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id)"
            ))
            conn.commit()
        except Exception:
            conn.rollback()
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan TEXT NOT NULL DEFAULT 'free'"
            ))
            conn.commit()
        except Exception:
            conn.rollback()
        try:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS pro_expires_at TIMESTAMPTZ"
            ))
            conn.commit()
        except Exception:
            conn.rollback()


def log_transcription(
    *,
    original_filename: str,
    stored_filename: str,
    file_size_bytes: int,
    model: str,
    status: str,
    processing_time_ms: int,
    transcript_length: int | None = None,
    client_ip: str | None = None,
    error_message: str | None = None,
    full_text: str | None = None,
    user_id: str | None = None,
):
    extra = None
    if STORE_FULL_TEXT and full_text is not None:
        extra = {"transcript": full_text}

    row = STTLog(
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_size_bytes=file_size_bytes,
        model=model,
        status=status,
        processing_time_ms=processing_time_ms,
        transcript_length=transcript_length,
        client_ip=client_ip,
        error_message=error_message,
        extra=extra,
        user_id=user_id,
    )

    with SessionLocal() as session:
        session.add(row)
        session.commit()
