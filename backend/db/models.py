"""Database models — Users, Subscriptions, Payments, Logs, Conversations."""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from backend.db.database import Base


def gen_id():
    return str(uuid.uuid4())[:12]


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, default="")
    role = Column(String, default="user")  # user | admin
    plan = Column(String, default="free")  # free | pro | premium
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    last_login = Column(DateTime, nullable=True)

    # Usage tracking
    messages_today = Column(Integer, default=0)
    messages_total = Column(Integer, default=0)
    last_message_date = Column(String, default="")

    # Contact + Location
    phone = Column(String, nullable=True)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    location_name = Column(String, nullable=True)  # "Hanoi, Vietnam"

    # Affiliate
    referral_code = Column(String, unique=True, nullable=True)
    referred_by = Column(String, nullable=True)        # user_id tầng 1
    level_2_parent = Column(String, nullable=True)     # user_id tầng 2

    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan = Column(String, nullable=False)  # free | pro | premium
    status = Column(String, default="active")  # active | cancelled | expired
    stripe_sub_id = Column(String, nullable=True)
    started_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="usd")
    status = Column(String, default="pending")  # pending | completed | failed | refunded
    stripe_payment_id = Column(String, nullable=True)
    plan = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="payments")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String, default="info")  # info | warning | error | critical
    source = Column(String, default="system")
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)


# Plan limits
PLAN_LIMITS = {
    "free": {"messages_per_day": 10, "max_conversations": 5, "price_monthly": 0},
    "pro": {"messages_per_day": 100, "max_conversations": 50, "price_monthly": 9.99},
    "premium": {"messages_per_day": 999999, "max_conversations": 999999, "price_monthly": 29.99},
}
