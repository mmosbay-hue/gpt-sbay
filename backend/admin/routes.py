"""Admin routes — user management, revenue, system logs."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.database import get_db
from backend.db.models import User, Subscription, Payment, SystemLog
from backend.auth.routes import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/stats")
def get_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Dashboard overview stats."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    pro_users = db.query(User).filter(User.plan == "pro").count()
    premium_users = db.query(User).filter(User.plan == "premium").count()
    paying_users = pro_users + premium_users

    # Revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(Payment.status == "completed").scalar() or 0
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.status == "completed", Payment.created_at >= month_start)
        .scalar() or 0
    )

    # Conversion
    conversion_rate = (paying_users / total_users * 100) if total_users > 0 else 0

    # Recent signups (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_users_week = db.query(User).filter(User.created_at >= week_ago).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "paying_users": paying_users,
        "pro_users": pro_users,
        "premium_users": premium_users,
        "conversion_rate": round(conversion_rate, 2),
        "total_revenue": round(total_revenue, 2),
        "monthly_revenue": round(monthly_revenue, 2),
        "new_users_week": new_users_week,
    }


@router.get("/users")
def list_users(
    page: int = 1,
    limit: int = 20,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "plan": u.plan,
                "role": u.role,
                "is_active": u.is_active,
                "phone": u.phone,
                "location_name": u.location_name,
                "latitude": u.latitude,
                "longitude": u.longitude,
                "messages_total": u.messages_total,
                "created_at": str(u.created_at),
                "last_login": str(u.last_login) if u.last_login else None,
            }
            for u in users
        ],
    }


@router.post("/users/{user_id}/toggle")
def toggle_user(user_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.get("/revenue")
def revenue_report(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    payments = (
        db.query(Payment)
        .filter(Payment.status == "completed")
        .order_by(Payment.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "amount": p.amount,
                "plan": p.plan,
                "created_at": str(p.created_at),
            }
            for p in payments
        ]
    }


@router.get("/logs")
def system_logs(
    level: str = "",
    limit: int = 50,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(SystemLog)
    if level:
        q = q.filter(SystemLog.level == level)
    logs = q.order_by(SystemLog.created_at.desc()).limit(limit).all()

    return {
        "logs": [
            {
                "id": l.id,
                "level": l.level,
                "source": l.source,
                "message": l.message,
                "created_at": str(l.created_at),
            }
            for l in logs
        ]
    }


@router.get("/usage")
def admin_usage(days: int = 7, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Usage tất cả users."""
    from backend.db.usage import get_all_users_usage
    users_usage = get_all_users_usage(days)
    result = []
    for u in users_usage:
        user = db.query(User).filter(User.id == u["user_id"]).first()
        result.append({
            "user_id": u["user_id"],
            "name": user.name if user else "?",
            "email": user.email if user else "?",
            "phone": user.phone if user else None,
            "plan": user.plan if user else "?",
            "total": u["total"],
        })
    return {"usage": result, "days": days}


@router.get("/usage/{user_id}")
def admin_user_usage(user_id: str, admin: User = Depends(require_admin)):
    """Usage chi tiết 1 user: ngày/tuần/tháng + so sánh."""
    from backend.db.usage import get_user_usage, get_usage_stats
    daily = get_user_usage(user_id, 30)
    stats = get_usage_stats(user_id)
    return {"daily": daily, "stats": stats}
