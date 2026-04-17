"""Seed admin user + test data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import bcrypt
from backend.db.database import SessionLocal, init_db
from backend.db.models import User, Subscription

def seed():
    init_db()
    db = SessionLocal()

    # Check if admin exists
    admin = db.query(User).filter(User.email == "admin@gptweb.com").first()
    if not admin:
        admin = User(
            email="admin@gptweb.com",
            password_hash=bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
            name="Admin",
            role="admin",
            plan="premium",
        )
        db.add(admin)
        db.flush()
        db.add(Subscription(user_id=admin.id, plan="premium", status="active"))
        db.commit()
        print(f"Admin created: admin@gptweb.com / admin123")
    else:
        print("Admin already exists")

    db.close()

if __name__ == "__main__":
    seed()
