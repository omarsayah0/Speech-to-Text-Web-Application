from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError

from backend.auth.security import decode_token
from backend.Database import SessionLocal, User
from backend.plans import PLAN_MODELS, PLAN_PRICES, PLAN_ORDER, normalize_plan, upgradeable_plans

router = APIRouter()

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
web = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _get_role(request: Request) -> str | None:
    """Returns the role from the database (not JWT), or None if not logged in."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        with SessionLocal() as session:
            user = session.get(User, user_id)
            return user.role if user else None
    except JWTError:
        return None


@router.get("/", include_in_schema=False)
def home(request: Request):
    role = _get_role(request)
    if role in ("admin", "moderator"):
        return RedirectResponse(url="/admin")
    if role == "user":
        return RedirectResponse(url="/app")
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    role = _get_role(request)
    if role in ("admin", "moderator"):
        return RedirectResponse(url="/admin")
    if role == "user":
        return RedirectResponse(url="/app")
    return web.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    role = _get_role(request)
    if role in ("admin", "moderator"):
        return RedirectResponse(url="/admin")
    if role == "user":
        return RedirectResponse(url="/app")
    return web.TemplateResponse("register.html", {"request": request})


@router.get("/app", response_class=HTMLResponse)
def app_page(request: Request):
    role = _get_role(request)
    if not role:
        return RedirectResponse(url="/login")

    plan = "tiny"
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            with SessionLocal() as session:
                user = session.get(User, user_id)
                if user:
                    plan = normalize_plan(getattr(user, "plan", "tiny"))
        except Exception:
            pass

    allowed_models = list(PLAN_MODELS.get(plan, {"tiny"}))

    return web.TemplateResponse("index.html", {
        "request": request,
        "plan": plan,
        "allowed_models": allowed_models,
    })


@router.get("/upgrade", response_class=HTMLResponse)
def upgrade_page(request: Request):
    role = _get_role(request)
    if not role:
        return RedirectResponse(url="/login")
    if role in ("admin", "moderator"):
        return RedirectResponse(url="/app")

    current_plan = "tiny"
    token = request.cookies.get("access_token")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if user:
                current_plan = normalize_plan(getattr(user, "plan", "tiny"))
    except Exception:
        pass

    # Show all plans except the current one
    other_plans = [p for p in PLAN_ORDER if p != current_plan]

    return web.TemplateResponse("upgrade.html", {
        "request": request,
        "current_plan": current_plan,
        "available_upgrades": other_plans,
        "plan_prices": PLAN_PRICES,
    })


@router.get("/upgrade/success", response_class=HTMLResponse)
def upgrade_success_page(request: Request):
    role = _get_role(request)
    if not role:
        return RedirectResponse(url="/login")

    plan = "tiny"
    token = request.cookies.get("access_token")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if user:
                plan = normalize_plan(getattr(user, "plan", "tiny"))
    except Exception:
        pass

    return web.TemplateResponse("upgrade_success.html", {"request": request, "plan": plan})
