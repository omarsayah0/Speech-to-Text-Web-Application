from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from jose import JWTError
from pydantic import BaseModel

from backend.Database import RefreshToken, SessionLocal, User
from backend.auth.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from backend.audit import save_audit_log  # ← new

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_TOKEN_MAX_AGE = 15 * 60        # 15 min
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 3600  # 7 days


class AuthRequest(BaseModel):
    email: str
    password: str


def _issue_tokens(response: Response, user: User) -> None:
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)

    with SessionLocal() as session:
        rt = RefreshToken(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        session.add(rt)
        session.commit()

    response.set_cookie("access_token", access, httponly=True, samesite="lax", max_age=ACCESS_TOKEN_MAX_AGE)
    response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax", max_age=REFRESH_TOKEN_MAX_AGE)


@router.post("/register", status_code=201)
def register(body: AuthRequest, response: Response):
    with SessionLocal() as session:
        if session.query(User).filter_by(email=body.email).first():
            raise HTTPException(400, "Email already registered")
        user = User(
            id=str(uuid4()),
            email=body.email,
            password_hash=hash_password(body.password),
            role="user",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)

    _issue_tokens(response, user)
    save_audit_log(user.email, "register", "New user registered")  # ← audit
    return {"message": "Registered successfully", "role": user.role}


@router.post("/login")
def login(body: AuthRequest, response: Response):
    with SessionLocal() as session:
        user = session.query(User).filter_by(email=body.email).first()
        if not user or not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "Invalid credentials")
        session.expunge(user)

    _issue_tokens(response, user)
    save_audit_log(user.email, "login", "User logged in")  # ← audit
    return {"message": "Logged in", "role": user.role}


@router.post("/refresh")
def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Missing refresh token")

    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        user_id: str = payload["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")

    token_hash = hash_token(token)
    with SessionLocal() as session:
        rt = session.query(RefreshToken).filter_by(token_hash=token_hash, revoked_at=None).first()
        if not rt:
            raise HTTPException(401, "Refresh token not found or already revoked")

        now = datetime.now(timezone.utc)
        expires = rt.expires_at if rt.expires_at.tzinfo else rt.expires_at.replace(tzinfo=timezone.utc)
        if expires < now:
            raise HTTPException(401, "Refresh token expired")

        rt.revoked_at = now
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(401, "User not found")
        session.expunge(user)
        session.commit()

    _issue_tokens(response, user)
    return {"message": "Tokens refreshed"}


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    user_email = None

    if token:
        token_hash = hash_token(token)
        with SessionLocal() as session:
            rt = session.query(RefreshToken).filter_by(token_hash=token_hash, revoked_at=None).first()
            if rt:
                # Grab email for the audit log before revoking
                user = session.get(User, rt.user_id)
                if user:
                    user_email = user.email
                rt.revoked_at = datetime.now(timezone.utc)
                session.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    save_audit_log(user_email, "logout", "User logged out")  # ← audit
    return {"message": "Logged out"}
