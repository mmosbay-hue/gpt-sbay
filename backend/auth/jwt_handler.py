"""JWT token creation + verification."""
import os
import jwt
from datetime import datetime, timedelta, timezone
from backend.config import JWT_SECRET

SECRET_KEY = JWT_SECRET or os.getenv("JWT_SECRET", "")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET is not set. Please configure it in .env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_token(user_id: str, email: str, role: str = "user") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
