
"""Database configuration for NammaPrayana."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Default to SQLite inside the backend directory if DATABASE_URL is not set.
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "nammaprayana.db"

raw_db_url = os.getenv("DATABASE_URL")

if raw_db_url:
    # Normalize legacy postgres:// scheme to postgresql:// for SQLAlchemy
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = raw_db_url
else:
    DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

# Configure engine arguments depending on dialect
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
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
