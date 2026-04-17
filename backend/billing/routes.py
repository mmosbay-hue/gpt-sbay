"""Billing routes — plans, upgrade, payment history."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.database import get_db
from backend.db.models import User, Subscription, Payment, PLAN_LIMITS
from backend.auth.routes import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


class UpgradeRequest(BaseModel):
    plan: str  # pro | premium


@router.get("/plans")
def get_plans():
    """Get available plans with pricing."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "currency": "usd",
                "interval": "month",
                "features": [
                    f"{PLAN_LIMITS['free']['messages_per_day']} messages/day",
                    f"{PLAN_LIMITS['free']['max_conversations']} conversations",
                    "Basic chat",
                ],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": PLAN_LIMITS["pro"]["price_monthly"],
                "currency": "usd",
                "interval": "month",
                "features": [
                    f"{PLAN_LIMITS['pro']['messages_per_day']} messages/day",
                    f"{PLAN_LIMITS['pro']['max_conversations']} conversations",
                    "Priority support",
                    "Advanced models",
                ],
                "popular": True,
            },
            {
                "id": "premium",
                "name": "Premium",
                "price": PLAN_LIMITS["premium"]["price_monthly"],
                "currency": "usd",
                "interval": "month",
                "features": [
                    "Unlimited messages",
                    "Unlimited conversations",
                    "Priority support",
                    "All models",
                    "API access",
                ],
            },
        ]
    }


@router.post("/upgrade")
def upgrade_plan(
    req: UpgradeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.plan not in ("pro", "premium"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    if user.plan == req.plan:
        raise HTTPException(status_code=400, detail="Already on this plan")

    price = PLAN_LIMITS[req.plan]["price_monthly"]

    # Create payment record
    payment = Payment(
        user_id=user.id,
        amount=price,
        currency="usd",
        status="completed",  # MVP: auto-complete. Production: Stripe webhook
        plan=req.plan,
    )
    db.add(payment)

    # Create/update subscription
    # Cancel old active subs
    old_subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .all()
    )
    for sub in old_subs:
        sub.status = "cancelled"
        sub.cancelled_at = datetime.now(timezone.utc)

    new_sub = Subscription(
        user_id=user.id,
        plan=req.plan,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(new_sub)

    # Update user plan
    user.plan = req.plan
    db.commit()

    # Affiliate: tính hoa hồng
    try:
        from backend.affiliate.routes import calculate_commissions
        calculate_commissions(user.id, price, payment.id, db)
    except Exception:
        pass  # không block upgrade nếu affiliate lỗi

    return {
        "message": f"Upgraded to {req.plan}",
        "plan": req.plan,
        "price": price,
        "expires_at": str(new_sub.expires_at),
    }


@router.post("/cancel")
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.plan == "free":
        raise HTTPException(status_code=400, detail="Already on free plan")

    active_sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .first()
    )
    if active_sub:
        active_sub.status = "cancelled"
        active_sub.cancelled_at = datetime.now(timezone.utc)

    user.plan = "free"
    db.commit()

    return {"message": "Subscription cancelled. Downgraded to free."}


@router.get("/history")
def payment_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payments = (
        db.query(Payment)
        .filter(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(50)
        .all()
    )
    return {
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status,
                "plan": p.plan,
                "created_at": str(p.created_at),
            }
            for p in payments
        ]
    }


@router.get("/usage")
def get_usage(
    user: User = Depends(get_current_user),
):
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    return {
        "plan": user.plan,
        "messages_today": user.messages_today,
        "messages_limit": limits["messages_per_day"],
        "messages_total": user.messages_total,
        "conversations_limit": limits["max_conversations"],
    }
