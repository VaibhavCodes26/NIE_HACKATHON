"""Authentication routes for NammaPrayana.

Endpoints:
  POST /api/auth/signup        — username + password registration
  POST /api/auth/login         — username + password login
  POST /api/auth/google        — Google ID-token login/registration
  GET  /api/auth/me            — return current authenticated user
  POST /api/auth/logout        — invalidate session

Sessions use a cryptographically random token stored in an HttpOnly cookie.
The backend is the sole source of truth; no sensitive data is sent to the client.
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import generate_session_token, hash_password, session_expiry, verify_password
from app.database import get_db
from app.models import User, UserSession
from app.services.rate_limiter import rate_limit_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Cookie cleanup helper (ensures legacy persistent cookies are removed)
# ---------------------------------------------------------------------------

COOKIE_NAME = "np_session"


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def _clear_session_cookie(response: Response) -> None:
    """Clear legacy cookie from client browser to guarantee tab-scoped isolation."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        samesite="lax",
        secure=_is_production(),
    )


# ---------------------------------------------------------------------------
# Session dependency — tab-scoped via explicit Bearer token in Authorization header
# ---------------------------------------------------------------------------

def get_session_token(
    request: Request,
) -> str | None:
    """Extract session token strictly from Authorization: Bearer header.
    
    Tab-scoped authentication requires that newly opened tabs without
    tab-specific tokens in sessionStorage cannot be authenticated via ambient cookies.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def get_current_user(
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that returns the authenticated User or raises HTTP 401."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    session = db.scalar(
        select(UserSession).where(UserSession.token == token)
    )
    if not session or session.is_expired():
        raise HTTPException(status_code=401, detail="Session expired or invalid.")

    return session.user


def get_optional_user(
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> User | None:
    """Dependency that returns the User or None if unauthenticated."""
    if not token:
        return None
    session = db.scalar(
        select(UserSession).where(UserSession.token == token)
    )
    if not session or session.is_expired():
        return None
    return session.user


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class GoogleLoginRequest(BaseModel):
    id_token: str


class AuthConfigResponse(BaseModel):
    google_client_id: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    created_at: str
    token: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_session(user: User, db: Session, response: Response) -> UserResponse:
    """Create a new session record and return the tab-scoped session token."""
    token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        token=token,
        expires_at=session_expiry(),
    )
    db.add(session)
    db.commit()

    # Clear any old legacy cookie from the client browser
    _clear_session_cookie(response)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at.isoformat(),
        token=token,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signup", status_code=201)
def signup(
    body: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
) -> UserResponse:
    """Register a new user with username and password."""
    if body.password != body.confirm_password:
        raise HTTPException(status_code=422, detail="Passwords do not match.")

    # Basic password complexity: at least 8 chars (already enforced by Field).
    # Enforce that username is clean.
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=422, detail="Username must not be blank.")

    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        raise HTTPException(status_code=409, detail="Username is already taken.")

    user = User(
        username=username,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _create_session(user, db, response)


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
) -> UserResponse:
    """Authenticate with username and password."""
    username = body.username.strip()
    user = db.scalar(select(User).where(User.username == username))

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    return _create_session(user, db, response)


@router.post("/google")
def google_login(
    body: GoogleLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Authenticate or register via Google Identity Services ID token."""
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        raise HTTPException(
            status_code=501,
            detail=(
                "Google authentication is not configured. "
                "Set GOOGLE_CLIENT_ID in the backend .env file."
            ),
        )

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        request_adapter = google_requests.Request()
        id_info = google_id_token.verify_oauth2_token(
            body.id_token,
            request_adapter,
            google_client_id,
        )
    except Exception as exc:
        print(f"[GOOGLE AUTH ERROR] {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=401,
            detail="Google authentication token verification failed.",
        ) from exc

    google_sub = id_info.get("sub")
    if not google_sub:
        raise HTTPException(status_code=401, detail="Google token missing 'sub' claim.")

    # Look up by stable Google subject identifier.
    user = db.scalar(select(User).where(User.google_sub == google_sub))

    if user is None:
        # New Google user — create an account.
        email = id_info.get("email")
        # Derive a username from email or sub.
        base_username = (email.split("@")[0] if email else f"user_{google_sub[:8]}")
        base_username = base_username[:60].replace(".", "_")
        username = base_username
        suffix = 1
        while db.scalar(select(User).where(User.username == username)):
            username = f"{base_username}_{suffix}"
            suffix += 1

        user = User(
            username=username,
            google_sub=google_sub,
            email=email,
            password_hash=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _create_session(user, db, response)


@router.get("/me")
def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/logout")
def logout(
    response: Response,
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> dict:
    """Invalidate the current session."""
    if token:
        session = db.scalar(select(UserSession).where(UserSession.token == token))
        if session:
            db.delete(session)
            db.commit()

    _clear_session_cookie(response)
    return {"message": "Logged out successfully."}


@router.get("/config")
def auth_config() -> AuthConfigResponse:
    """Return public authentication configuration (Google Client ID)."""
    return AuthConfigResponse(
        google_client_id=os.getenv("GOOGLE_CLIENT_ID") or None,
    )
