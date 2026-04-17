"""Usage tracking — theo dõi sử dụng từng tài khoản theo ngày/tuần/tháng."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from datetime import datetime, timezone, timedelta
from backend.db.database import Base, SessionLocal
import uuid


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # chat | login | upload | gpt_chat
    date = Column(String, nullable=False)  # YYYY-MM-DD
    count = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def log_usage(user_id: str, action: str = "chat"):
    """Ghi log usage cho user."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        existing = db.query(UsageLog).filter(
            UsageLog.user_id == user_id,
            UsageLog.action == action,
            UsageLog.date == today
        ).first()
        if existing:
            existing.count += 1
        else:
            db.add(UsageLog(user_id=user_id, action=action, date=today))
        db.commit()
    finally:
        db.close()


def get_user_usage(user_id: str, days: int = 30) -> list[dict]:
    """Lấy usage từng ngày trong N ngày gần nhất."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        rows = db.query(UsageLog).filter(
            UsageLog.user_id == user_id,
            UsageLog.date >= start
        ).order_by(UsageLog.date.desc()).all()
        return [{"date": r.date, "action": r.action, "count": r.count} for r in rows]
    finally:
        db.close()


def get_usage_stats(user_id: str) -> dict:
    """Thống kê usage: hôm nay, 7 ngày, 30 ngày, so sánh."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_week = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    db = SessionLocal()
    try:
        def sum_count(start, end=None):
            q = db.query(UsageLog).filter(UsageLog.user_id == user_id, UsageLog.date >= start)
            if end:
                q = q.filter(UsageLog.date < end)
            return sum(r.count for r in q.all())

        today_count = sum_count(today)
        week_count = sum_count(week_ago)
        prev_week_count = sum_count(prev_week, week_ago)
        month_count = sum_count(month_ago)

        # So sánh tuần này vs tuần trước
        week_change = 0
        if prev_week_count > 0:
            week_change = round((week_count - prev_week_count) / prev_week_count * 100)

        return {
            "today": today_count,
            "week": week_count,
            "prev_week": prev_week_count,
            "month": month_count,
            "week_change_pct": week_change,
        }
    finally:
        db.close()


def get_all_users_usage(days: int = 7) -> list[dict]:
    """Admin: usage tất cả users trong N ngày."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        from sqlalchemy import func
        rows = db.query(
            UsageLog.user_id,
            func.sum(UsageLog.count).label("total")
        ).filter(UsageLog.date >= start).group_by(UsageLog.user_id).order_by(func.sum(UsageLog.count).desc()).all()
        return [{"user_id": r.user_id, "total": r.total} for r in rows]
    finally:
        db.close()
