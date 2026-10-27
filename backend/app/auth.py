"""Authentication utilities for NammaPrayana.

Uses passlib for bcrypt password hashing and itsdangerous
for signing session tokens stored in HttpOnly cookies.
"""

import os
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using bcrypt, truncating to 72 bytes."""
    pwd_bytes = plaintext.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        pwd_bytes = plaintext.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session token generation
# ---------------------------------------------------------------------------

SESSION_BYTES = 32


def generate_session_token() -> str:
    """Return a cryptographically secure, URL-safe session token."""
    return secrets.token_urlsafe(SESSION_BYTES)


# ---------------------------------------------------------------------------
# Session lifetime
# ---------------------------------------------------------------------------

SESSION_LIFETIME_DAYS = 1
SESSION_LIFETIME_HOURS = 24


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=SESSION_LIFETIME_HOURS)
