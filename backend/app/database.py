
"""Database configuration for NammaPrayana."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Default to SQLite database inside the backend/app directory
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "nammaprayana.db"

raw_db_url = os.getenv("DATABASE_URL")
if raw_db_url:
    # Normalize postgres:// scheme (used by Render, Heroku) to postgresql://
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = raw_db_url
else:
    DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# SQLite requires check_same_thread=False for multithreaded FastAPI workers
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

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
