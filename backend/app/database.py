
"""Database configuration for NammaPrayana."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Store the database file inside the backend directory.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "nammaprayana.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# SQLite requires this option for FastAPI's request handling.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# A database session will be created for each request.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""
    pass


def get_db():
    """Provide a database session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all registered database tables."""
    # Import models so SQLAlchemy registers their tables.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
