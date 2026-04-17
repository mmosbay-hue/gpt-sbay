"""Affiliate 2-tier models."""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from datetime import datetime, timezone
from backend.db.database import Base
import uuid


def gen_id():
    return str(uuid.uuid4())[:12]


def gen_ref_code():
    return uuid.uuid4().hex[:8].upper()


class Commission(Base):
    __tablename__ = "commissions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, nullable=False)           # Người nhận hoa hồng
    source_user_id = Column(String, nullable=False)     # Người tạo doanh thu
    payment_id = Column(String, nullable=False)         # Payment gốc
    amount = Column(Float, nullable=False)              # Số tiền hoa hồng
    level = Column(Integer, nullable=False)             # 1 = tầng 1 (20%), 2 = tầng 2 (10%)
    status = Column(String, default="pending")          # pending | paid | cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Commission rates
TIER1_RATE = 0.20  # 20%
TIER2_RATE = 0.10  # 10%
