from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.Database import SessionLocal, User
from backend.auth.deps import get_current_user
from backend.plans import PLAN_ORDER, PLAN_PRICES, normalize_plan
from backend.audit import save_audit_log  # ← new

router = APIRouter(prefix="/subscription", tags=["subscription"])

PAID_PLAN_DURATION_DAYS = 30


class UpgradeRequest(BaseModel):
    plan: str                  # target plan: "small", "medium", or "large"
    card_number: str = ""      # dummy — ignored for free downgrades
    expiry: str = ""
    cvc: str = ""


@router.post("/upgrade")
def upgrade_plan(body: UpgradeRequest, current_user: User = Depends(get_current_user)):
    """
    Simulate a successful plan change.
    Card details are accepted but completely ignored — this is a dummy flow.
    """
    target_plan = body.plan.lower()

    if target_plan not in PLAN_ORDER:
        raise HTTPException(400, f"Invalid plan '{target_plan}'. Choose from: {', '.join(PLAN_ORDER)}")

    current_plan = normalize_plan(getattr(current_user, "plan", "tiny"))

    if target_plan == current_plan:
        raise HTTPException(400, f"You are already on the {target_plan} plan.")

    # For paid plans, validate dummy card fields are present
    price = PLAN_PRICES[target_plan]
    if price > 0:
        if not body.card_number.strip() or not body.expiry.strip() or not body.cvc.strip():
            raise HTTPException(422, "Please fill in all payment fields.")

    # Set expiry only for paid plans
    new_expires_at = None
    if price > 0:
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=PAID_PLAN_DURATION_DAYS)

    with SessionLocal() as session:
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(404, "User not found")
        user.plan = target_plan
        user.pro_expires_at = new_expires_at
        session.commit()

    save_audit_log(current_user.email, "change_plan", f"Changed plan from '{current_plan}' to '{target_plan}'")  # ← audit

    return {
        "message": f"Plan changed to {target_plan} successfully",
        "plan": target_plan,
        "price": price,
        "expires_at": new_expires_at.isoformat() if new_expires_at else None,
    }
