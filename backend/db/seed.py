"""Seed admin user + test data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import bcrypt
from backend.db.database import SessionLocal, init_db
from backend.db.models import User, Subscription

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gptweb.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

def seed():
    if not ADMIN_PASSWORD:
        print("ERROR: ADMIN_PASSWORD env var is required to seed admin user.")
        return

    init_db()
    db = SessionLocal()

    admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
            name="Admin",
            role="admin",
            plan="premium",
        )
        db.add(admin)
        db.flush()
        db.add(Subscription(user_id=admin.id, plan="premium", status="active"))
        db.commit()
        print(f"Admin created: {ADMIN_EMAIL}")
    else:
        print("Admin already exists")

    db.close()

if __name__ == "__main__":
    seed()
