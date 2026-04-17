"""Auth routes — register, login, me, forgot password."""
import bcrypt
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.db.database import get_db
from backend.db.models import User, Subscription
from backend.auth.jwt_handler import create_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============ Schemas ============
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""
    phone: str = ""
    ref: str = ""  # referral code


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ============ Helpers ============
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Extract user from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth[7:]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


# ============ OTP ============
class OTPRequest(BaseModel):
    phone: str
    email: str = ""
    name: str = ""

class OTPVerify(BaseModel):
    phone: str
    code: str


@router.post("/send-otp")
async def send_otp(req: OTPRequest):
    """Gửi mã OTP qua Zalo."""
    phone = req.phone.strip()
    if not phone or len(phone) < 9:
        raise HTTPException(status_code=400, detail="Số điện thoại không hợp lệ")

    from backend.auth.otp import generate_otp, send_otp_zalo
    code = generate_otp(phone, req.email, "register")
    msg = await send_otp_zalo(phone, code, req.name)

    return {"sent": True, "message": "Mã xác thực đã gửi qua Zalo. Vui lòng kiểm tra.", "expires_in": 300}


@router.post("/verify-otp")
def verify_otp_route(req: OTPVerify):
    """Xác thực mã OTP."""
    from backend.auth.otp import verify_otp
    ok = verify_otp(req.phone.strip(), req.code.strip())
    if not ok:
        raise HTTPException(status_code=400, detail="Mã xác thực sai hoặc đã hết hạn")
    return {"verified": True}


# ============ Routes ============
@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check existing
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Create user with referral tracking
    import uuid
    ref_code = uuid.uuid4().hex[:8].upper()

    # Find referrer
    referred_by = None
    level_2_parent = None
    if req.ref:
        referrer = db.query(User).filter(User.referral_code == req.ref).first()
        if referrer and referrer.email != req.email:  # cấm tự ref
            referred_by = referrer.id
            # Tầng 2 = parent của referrer
            if referrer.referred_by:
                level_2_parent = referrer.referred_by

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name or req.email.split("@")[0],
        phone=req.phone or None,
        plan="free",
        referral_code=ref_code,
        referred_by=referred_by,
        level_2_parent=level_2_parent,
    )
    db.add(user)
    db.flush()

    # Create free subscription
    sub = Subscription(user_id=user.id, plan="free", status="active")
    db.add(sub)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.email, user.role)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "plan": user.plan,
            "role": user.role,
        },
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not check_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_token(user.id, user.email, user.role)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "plan": user.plan,
            "role": user.role,
        },
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "plan": user.plan,
        "role": user.role,
        "messages_today": user.messages_today,
        "messages_total": user.messages_total,
        "latitude": user.latitude,
        "longitude": user.longitude,
        "location_name": user.location_name,
        "created_at": str(user.created_at),
    }


@router.post("/update-location")
def update_location(data: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cập nhật vị trí + số điện thoại."""
    if data.get("latitude"):
        user.latitude = str(data["latitude"])
    if data.get("longitude"):
        user.longitude = str(data["longitude"])
    if data.get("location_name"):
        user.location_name = data["location_name"]
    if data.get("phone"):
        user.phone = data["phone"]
    db.commit()
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}

    # In production: send email with reset token
    # For MVP: generate token and return it
    reset_token = create_token(user.id, user.email, "reset")
    return {"message": "If the email exists, a reset link has been sent", "reset_token": reset_token}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = verify_token(req.token)
    if not payload or payload.get("role") != "reset":
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(req.new_password)
    db.commit()

    return {"message": "Password reset successfully"}
