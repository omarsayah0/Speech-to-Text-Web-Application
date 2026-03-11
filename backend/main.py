import os
from uuid import uuid4

from fastapi import FastAPI

from backend.Database import SessionLocal, User, init_db
from backend.auth.security import hash_password
from backend.auth.routes import router as auth_router
from backend.routes.web import router as web_router
from backend.routes.transcriptions import router as transcriptions_router
from backend.routes.logs import router as logs_router
from backend.routes.subscription import router as subscription_router

# Admin routers
from backend.admin.routes_users import router as admin_users_router
from backend.admin.routes_logs import router as admin_logs_router
from backend.admin.routes_permissions import router as admin_permissions_router
from backend.admin.routes_roles import router as admin_roles_router
from backend.admin.routes_roles import user_router as admin_user_roles_router
from backend.admin.web import router as admin_web_router
from backend.admin.seed_rbac import seed_rbac

app = FastAPI()

app.include_router(web_router)
app.include_router(auth_router)
app.include_router(transcriptions_router)
app.include_router(logs_router)
app.include_router(subscription_router)

# Admin
app.include_router(admin_web_router)
app.include_router(admin_users_router)
app.include_router(admin_logs_router)
app.include_router(admin_permissions_router)
app.include_router(admin_roles_router)
app.include_router(admin_user_roles_router)


@app.on_event("startup")
def startup():
    init_db()
    _seed_admin()
    seed_rbac()


def _seed_admin():
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        return
    with SessionLocal() as session:
        if session.query(User).filter_by(email=email).first():
            return
        admin = User(
            id=str(uuid4()),
            email=email,
            password_hash=hash_password(password),
            role="admin",
            plan="pro",
        )
        session.add(admin)
        session.commit()
