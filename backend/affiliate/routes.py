"""Affiliate 2-tier routes — dashboard, tree, commissions, tracking."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.database import get_db
from backend.db.models import User, Payment
from backend.affiliate.models import Commission, TIER1_RATE, TIER2_RATE
from backend.auth.routes import get_current_user

router = APIRouter(prefix="/api/affiliate", tags=["affiliate"])


def ensure_ref_code(user: User, db: Session):
    """Tạo referral code nếu chưa có."""
    if not user.referral_code:
        user.referral_code = uuid.uuid4().hex[:8].upper()
        db.commit()
    return user.referral_code


@router.get("/dashboard")
def affiliate_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ref_code = ensure_ref_code(user, db)

    # Đếm tầng 1
    tier1_count = db.query(User).filter(User.referred_by == user.id).count()
    # Đếm tầng 2
    tier2_count = db.query(User).filter(User.level_2_parent == user.id).count()

    # Tổng commission
    total_earned = db.query(func.sum(Commission.amount)).filter(
        Commission.user_id == user.id, Commission.status != "cancelled"
    ).scalar() or 0

    # Commission hôm nay
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_earned = db.query(func.sum(Commission.amount)).filter(
        Commission.user_id == user.id,
        Commission.created_at >= today,
        Commission.status != "cancelled"
    ).scalar() or 0

    # Pending
    pending = db.query(func.sum(Commission.amount)).filter(
        Commission.user_id == user.id, Commission.status == "pending"
    ).scalar() or 0

    return {
        "referral_code": ref_code,
        "referral_link": f"/register?ref={ref_code}",
        "tier1_count": tier1_count,
        "tier2_count": tier2_count,
        "total_earned": round(total_earned, 2),
        "today_earned": round(today_earned, 2),
        "pending": round(pending, 2),
        "tier1_rate": f"{int(TIER1_RATE * 100)}%",
        "tier2_rate": f"{int(TIER2_RATE * 100)}%",
    }


@router.get("/tree")
def affiliate_tree(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Sơ đồ cây affiliate."""
    tier1_users = db.query(User).filter(User.referred_by == user.id).all()

    tree = []
    for u1 in tier1_users:
        tier2_users = db.query(User).filter(User.referred_by == u1.id).all()
        tree.append({
            "id": u1.id,
            "name": u1.name or u1.email.split("@")[0],
            "email": u1.email,
            "plan": u1.plan,
            "level": 1,
            "joined": str(u1.created_at),
            "children": [
                {
                    "id": u2.id,
                    "name": u2.name or u2.email.split("@")[0],
                    "email": u2.email,
                    "plan": u2.plan,
                    "level": 2,
                    "joined": str(u2.created_at),
                }
                for u2 in tier2_users
            ],
        })

    return {"tree": tree, "total_tier1": len(tier1_users)}


@router.get("/commissions")
def affiliate_commissions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Bảng hoa hồng."""
    comms = (
        db.query(Commission)
        .filter(Commission.user_id == user.id)
        .order_by(Commission.created_at.desc())
        .limit(50)
        .all()
    )

    results = []
    for c in comms:
        source = db.query(User).filter(User.id == c.source_user_id).first()
        results.append({
            "id": c.id,
            "source_name": source.name or source.email.split("@")[0] if source else "Unknown",
            "amount": c.amount,
            "level": c.level,
            "status": c.status,
            "created_at": str(c.created_at),
        })

    return {"commissions": results}


def calculate_commissions(payment_user_id: str, payment_amount: float, payment_id: str, db: Session):
    """Tính và lưu hoa hồng khi có thanh toán mới."""
    user = db.query(User).filter(User.id == payment_user_id).first()
    if not user:
        return

    # Tầng 1: parent trực tiếp
    if user.referred_by:
        comm1 = Commission(
            user_id=user.referred_by,
            source_user_id=payment_user_id,
            payment_id=payment_id,
            amount=round(payment_amount * TIER1_RATE, 2),
            level=1,
        )
        db.add(comm1)

    # Tầng 2: parent của parent
    if user.level_2_parent:
        comm2 = Commission(
            user_id=user.level_2_parent,
            source_user_id=payment_user_id,
            payment_id=payment_id,
            amount=round(payment_amount * TIER2_RATE, 2),
            level=2,
        )
        db.add(comm2)

    db.commit()
