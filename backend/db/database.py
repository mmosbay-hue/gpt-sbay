"""Database engine + session — SQLite for MVP, swap to PostgreSQL for production."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "gptweb.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    # Import all models so Base knows about them
    import backend.db.models  # noqa
    import backend.db.usage  # noqa
    import backend.gpts.models  # noqa
    import backend.affiliate.models  # noqa
    Base.metadata.create_all(bind=engine)
