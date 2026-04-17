"""OTP system — tạo mã, lưu DB, verify, gửi qua Zalo."""
import random
import sqlite3
import os
import httpx
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "gptweb.db")
ADMIN_ZALO = "0815340488"
OTP_EXPIRY_MINUTES = 5


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        email TEXT,
        code TEXT NOT NULL,
        purpose TEXT DEFAULT 'register',
        used INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn


def generate_otp(phone: str, email: str = "", purpose: str = "register") -> str:
    """Tạo mã OTP 6 số, lưu DB, trả về code."""
    code = str(random.randint(100000, 999999))
    now = datetime.now()
    expires = now + timedelta(minutes=OTP_EXPIRY_MINUTES)

    conn = _get_conn()
    # Xóa OTP cũ chưa dùng của phone này
    conn.execute("UPDATE otp_codes SET used = 1 WHERE phone = ? AND used = 0", (phone,))
    conn.execute(
        "INSERT INTO otp_codes (phone, email, code, purpose, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (phone, email, code, purpose, now.isoformat(), expires.isoformat())
    )
    conn.commit()
    conn.close()
    return code


def verify_otp(phone: str, code: str) -> bool:
    """Xác thực OTP. Trả về True nếu đúng + chưa hết hạn."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, expires_at FROM otp_codes WHERE phone = ? AND code = ? AND used = 0 ORDER BY id DESC LIMIT 1",
        (phone, code)
    ).fetchone()

    if not row:
        conn.close()
        return False

    # Check hết hạn
    expires = datetime.fromisoformat(row[1])
    if datetime.now() > expires:
        conn.close()
        return False

    # Đánh dấu đã dùng
    conn.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (row[0],))
    conn.commit()
    conn.close()
    return True


async def send_otp_zalo(phone: str, code: str, name: str = ""):
    """Gửi OTP qua Zalo. Fallback: log vào DB để admin xem."""
    message = f"[SbayAI] Mã xác thực của {name or phone}: {code}. Hết hạn sau {OTP_EXPIRY_MINUTES} phút. Không chia sẻ mã này."

    # TODO: Kết nối Zalo OA API khi có credentials
    # Hiện tại: lưu vào DB + gửi webhook nếu có
    try:
        # Gửi qua Zalo OA API (cần access_token)
        zalo_oa_token = os.getenv("ZALO_OA_TOKEN", "")
        if zalo_oa_token:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    "https://openapi.zalo.me/v3.0/oa/message/cs",
                    headers={"access_token": zalo_oa_token},
                    json={
                        "recipient": {"user_id": phone},
                        "message": {"text": message}
                    }
                )
    except Exception:
        pass

    # Lưu log để admin xem OTP (backup)
    try:
        conn = _get_conn()
        conn.execute("CREATE TABLE IF NOT EXISTS otp_logs (id INTEGER PRIMARY KEY, phone TEXT, code TEXT, message TEXT, sent_at TEXT)")
        conn.execute("INSERT INTO otp_logs (phone, code, message, sent_at) VALUES (?, ?, ?, ?)",
                     (phone, code, message, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return message
