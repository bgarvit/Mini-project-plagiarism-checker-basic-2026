"""Authentication API routes (email/password + Google OAuth-ready)."""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.auth_utils import (
    create_access_token,
    get_current_user,
    hash_password,
    require_user,
    verify_password,
)
from app.config import GOOGLE_CLIENT_ID
from app.database.sqlite_users import (
    create_reset_token,
    get_or_create_oauth_user,
    get_statistics,
    mark_token_used,
    record_login_event,
    verify_reset_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    institution: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=40)
    picture: str | None = Field(default=None, max_length=700_000)
    accepted_terms: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class GoogleLoginRequest(BaseModel):
    """Accept a Google ID token, access token, or a demo profile payload.

    Production: send `id_token` from Google Identity Services / Firebase / Auth0.
    Demo: if GOOGLE_CLIENT_ID is unset, you may send email + name for local testing.
    """

    id_token: str | None = None
    access_token: str | None = None
    email: EmailStr | None = None
    name: str | None = None
    picture: str | None = None
    provider: str = "google"


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    name: str | None = None
    picture: str | None = None
    auth_provider: str = "local"
    phone: str | None = None
    institution: str | None = None
    role: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    picture: str | None = None
    auth_provider: str = "local"
    phone: str | None = None
    institution: str | None = None
    role: str | None = None


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    institution: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=40)
    # Data URL (image/jpeg|png|webp|gif) or empty string to clear. Omit to leave unchanged.
    picture: str | None = Field(default=None, max_length=700_000)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8)


def _auth_response(user: dict) -> AuthResponse:
    token = create_access_token(user["id"], user["email"], user.get("name"))
    return AuthResponse(
        access_token=token,
        email=user["email"],
        name=user.get("name"),
        picture=user.get("picture"),
        auth_provider=user.get("auth_provider") or "local",
        phone=user.get("phone"),
        institution=user.get("institution"),
        role=user.get("role"),
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> AuthResponse:
    if not payload.accepted_terms:
        raise HTTPException(
            status_code=400,
            detail="You must accept the Terms of Service and Privacy Policy.",
        )
    picture = None
    if payload.picture:
        normalized = _normalize_picture(payload.picture)
        picture = normalized or None
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    phone = (payload.phone or "").strip() or None
    institution = (payload.institution or "").strip() or None
    role = (payload.role or "").strip() or None
    allowed_roles = {None, "student", "teacher", "researcher", "professional", "other"}
    if role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Invalid role selection")
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (payload.email.lower(),)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        cursor = conn.execute(
            """INSERT INTO users
               (email, password_hash, name, picture, auth_provider, phone, institution, role, accepted_terms)
               VALUES (?, ?, ?, ?, 'local', ?, ?, ?, 1)""",
            (
                payload.email.lower(),
                hash_password(payload.password),
                name,
                picture,
                phone,
                institution,
                role,
            ),
        )
        user_id = cursor.lastrowid
    record_login_event(
        user_id=user_id,
        email=payload.email.lower(),
        name=name,
        event_type="register",
        auth_provider="local",
    )
    return _auth_response(
        {
            "id": user_id,
            "email": payload.email.lower(),
            "name": name,
            "picture": picture,
            "auth_provider": "local",
            "phone": phone,
            "institution": institution,
            "role": role,
        }
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, name, picture, auth_provider, phone, institution, role FROM users WHERE email = ?",
            (payload.email.lower(),),
        ).fetchone()
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    record_login_event(
        user_id=row["id"],
        email=row["email"],
        name=row["name"],
        event_type="login",
        auth_provider=row["auth_provider"] or "local",
    )
    return _auth_response(
        {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "picture": row["picture"],
            "auth_provider": row["auth_provider"] or "local",
            "phone": row["phone"] if "phone" in row.keys() else None,
            "institution": row["institution"] if "institution" in row.keys() else None,
            "role": row["role"] if "role" in row.keys() else None,
        }
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict:
    """Request a password reset link for the given email."""
    email = payload.email.lower()
    
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email FROM users WHERE email = ? AND auth_provider = 'local'",
            (email,),
        ).fetchone()
    
    # Always return success to prevent email enumeration
    # In production, you would send an actual email here
    if row:
        token = create_reset_token(email)
        # Log the token for demo purposes (in production, send via email)
        print(f"[PASSWORD RESET] Token for {email}: {token}")
        print(f"[PASSWORD RESET] Reset link: https://your-app.garvit.app/reset-password.html?token={token}")
    
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest) -> AuthResponse:
    """Reset password using a valid token."""
    email = verify_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Verify user exists
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, picture, auth_provider, phone, institution, role FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.password), row["id"]),
        )
    
    # Mark token as used
    mark_token_used(payload.token)
    
    # Record login event
    record_login_event(
        user_id=row["id"],
        email=row["email"],
        name=row["name"],
        event_type="password_reset",
        auth_provider=row["auth_provider"] or "local",
    )
    
    return _auth_response(
        {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "picture": row["picture"],
            "auth_provider": row["auth_provider"] or "local",
        }
    )


async def _verify_google_id_token(id_token: str) -> dict[str, Any]:
    """Verify Google ID token via tokeninfo endpoint (simple, no extra deps).

    For production scale, prefer google-auth library or Firebase Admin SDK.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token (HTTP {resp.status_code}). Try again.",
        )
    data = resp.json()
    aud = data.get("aud")
    if GOOGLE_CLIENT_ID and aud != GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Google token audience mismatch. "
                "GOOGLE_CLIENT_ID must equal the Web Client ID used in the browser."
            ),
        )
    email = data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token missing email",
        )
    if data.get("email_verified") in ("false", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email not verified",
        )
    return {
        "email": email,
        "name": data.get("name") or data.get("given_name"),
        "picture": data.get("picture"),
        "sub": data.get("sub"),
    }


async def _verify_google_access_token(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google access token",
        )
    data = resp.json()
    email = data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google profile missing email",
        )
    return {
        "email": email,
        "name": data.get("name"),
        "picture": data.get("picture"),
        "sub": data.get("sub"),
    }


@router.post("/google", response_model=AuthResponse)
async def google_login(payload: GoogleLoginRequest) -> AuthResponse:
    """Exchange a Google credential for a Plagify JWT.

    Wire-up options:
    1. Google Identity Services → send `id_token`
    2. OAuth access token → send `access_token`
    3. Auth0 / Firebase → map their ID token into this endpoint (or add a sibling route)
    4. Demo (no GOOGLE_CLIENT_ID): send email (+ optional name/picture)
    """
    profile: dict[str, Any] | None = None

    if payload.id_token:
        profile = await _verify_google_id_token(payload.id_token)
    elif payload.access_token:
        profile = await _verify_google_access_token(payload.access_token)
    elif payload.email and not GOOGLE_CLIENT_ID:
        # Local/demo path when Google client is not configured
        profile = {
            "email": str(payload.email),
            "name": payload.name,
            "picture": payload.picture,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Provide id_token or access_token from Google. "
                "Or set GOOGLE_CLIENT_ID and use Google Sign-In on the client."
            ),
        )

    user = get_or_create_oauth_user(
        email=profile["email"],
        name=profile.get("name") or payload.name,
        picture=profile.get("picture") or payload.picture,
        provider=payload.provider or "google",
    )
    return _auth_response(user)


@router.get("/config")
def auth_config() -> dict:
    """Public client config so the frontend knows which providers are enabled."""
    return {
        "google_client_id": GOOGLE_CLIENT_ID or None,
        "google_enabled": bool(GOOGLE_CLIENT_ID),
        "demo_google": not bool(GOOGLE_CLIENT_ID),
    }


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(require_user)) -> UserResponse:
    # Refresh from DB so picture and extra fields are current
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, picture, auth_provider, phone, institution, role FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    def _col(r, key):
        try:
            return r[key]
        except (KeyError, IndexError):
            return None

    return UserResponse(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        picture=row["picture"],
        auth_provider=(row["auth_provider"] or "local"),
        phone=_col(row, "phone"),
        institution=_col(row, "institution"),
        role=_col(row, "role"),
    )


def _normalize_picture(value: str | None) -> str | None:
    """Validate optional data-URL profile image; empty string clears."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return ""  # clear
    if not cleaned.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Picture must be an image data URL")
    # data:image/png;base64,...
    header, _, rest = cleaned.partition(",")
    if ";base64" not in header or not rest:
        raise HTTPException(status_code=400, detail="Picture must be a base64 data URL")
    allowed = ("image/jpeg", "image/png", "image/webp", "image/gif")
    if not any(fmt in header for fmt in allowed):
        raise HTTPException(
            status_code=400,
            detail="Supported image types: JPEG, PNG, WebP, GIF",
        )
    # ~500KB decoded ≈ 700k chars encoded — already capped by Field max_length
    if len(cleaned) > 700_000:
        raise HTTPException(status_code=400, detail="Image is too large (max ~500 KB)")
    return cleaned


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest, user: dict = Depends(require_user)
) -> UserResponse:
    with get_connection() as conn:
        if payload.name is not None:
            conn.execute(
                "UPDATE users SET name = ? WHERE id = ?",
                (payload.name.strip() or None, user["id"]),
            )
        if payload.phone is not None:
            conn.execute(
                "UPDATE users SET phone = ? WHERE id = ?",
                ((payload.phone or "").strip() or None, user["id"]),
            )
        if payload.institution is not None:
            conn.execute(
                "UPDATE users SET institution = ? WHERE id = ?",
                ((payload.institution or "").strip() or None, user["id"]),
            )
        if payload.role is not None:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                ((payload.role or "").strip() or None, user["id"]),
            )
        if payload.picture is not None:
            normalized = _normalize_picture(payload.picture)
            # empty string clears the photo (store NULL)
            conn.execute(
                "UPDATE users SET picture = ? WHERE id = ?",
                (normalized if normalized else None, user["id"]),
            )
        row = conn.execute(
            "SELECT id, email, name, picture, auth_provider, phone, institution, role FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()

    def _col(r, key):
        try:
            return r[key]
        except (KeyError, IndexError):
            return None

    return UserResponse(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        picture=row["picture"],
        auth_provider=(row["auth_provider"] or "local"),
        phone=_col(row, "phone"),
        institution=_col(row, "institution"),
        role=_col(row, "role"),
    )


@router.get("/stats")
def stats(user: dict | None = Depends(get_current_user)) -> dict:
    user_id = user["id"] if user else None
    return get_statistics(user_id)