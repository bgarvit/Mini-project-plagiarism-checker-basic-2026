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
from app.database.sqlite_users import get_connection, get_or_create_oauth_user, get_statistics

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=120)
    picture: str | None = Field(default=None, max_length=700_000)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PasswordOtpRequest(BaseModel):
    """Request an OTP to change password (sent to account email)."""
    pass


class PasswordChangeRequest(BaseModel):
    otp: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)


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


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    picture: str | None = None
    auth_provider: str = "local"


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    # Data URL (image/jpeg|png|webp|gif) or empty string to clear. Omit to leave unchanged.
    picture: str | None = Field(default=None, max_length=700_000)


def _auth_response(user: dict) -> AuthResponse:
    token = create_access_token(user["id"], user["email"], user.get("name"))
    return AuthResponse(
        access_token=token,
        email=user["email"],
        name=user.get("name"),
        picture=user.get("picture"),
        auth_provider=user.get("auth_provider") or "local",
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest) -> AuthResponse:
    picture = None
    if payload.picture:
        normalized = _normalize_picture(payload.picture)
        picture = normalized or None
    name = payload.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (payload.email.lower(),)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, name, picture, auth_provider) VALUES (?, ?, ?, ?, 'local')",
            (payload.email.lower(), hash_password(payload.password), name, picture),
        )
        user_id = cursor.lastrowid
    return _auth_response(
        {
            "id": user_id,
            "email": payload.email.lower(),
            "name": name,
            "picture": picture,
            "auth_provider": "local",
        }
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, name, picture, auth_provider FROM users WHERE email = ?",
            (payload.email.lower(),),
        ).fetchone()
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
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
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token"
        )
    data = resp.json()
    if GOOGLE_CLIENT_ID and data.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token audience mismatch. Check GOOGLE_CLIENT_ID.",
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
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user.get("name"),
        picture=user.get("picture"),
        auth_provider=user.get("auth_provider") or "local",
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
        if payload.picture is not None:
            normalized = _normalize_picture(payload.picture)
            # empty string clears the photo
            conn.execute(
                "UPDATE users SET picture = ? WHERE id = ?",
                (normalized or None, user["id"]),
            )
        row = conn.execute(
            "SELECT id, email, name, picture, auth_provider FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
    return UserResponse(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        picture=row["picture"],
        auth_provider=row["auth_provider"] or "local",
    )


@router.get("/stats")
def stats(user: dict | None = Depends(get_current_user)) -> dict:
    user_id = user["id"] if user else None
    return get_statistics(user_id)


def _ensure_otp_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_otps (
            user_id INTEGER PRIMARY KEY,
            otp_code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )


@router.post("/password/request-otp")
def request_password_otp(user: dict = Depends(require_user)) -> dict:
    """Generate a one-time code for password change. In production this is emailed only.

    For local/demo setups without SMTP, the code is also returned as `demo_otp`
    so you can complete the flow. Never rely on that field in production.
    """
    import random
    from datetime import datetime, timedelta, timezone

    code = f"{random.randint(100000, 999999)}"
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    with get_connection() as conn:
        _ensure_otp_table(conn)
        conn.execute(
            "INSERT OR REPLACE INTO password_otps (user_id, otp_code, expires_at) VALUES (?, ?, ?)",
            (user["id"], code, expires),
        )
        email_row = conn.execute(
            "SELECT email FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
    email = email_row["email"] if email_row else user.get("email")
    # Prototype: no SMTP configured — log and return demo_otp for testing
    print(f"[Plagify OTP] password change code for {email}: {code} (expires in 10 min)")
    return {
        "ok": True,
        "message": f"A one-time password was sent to {email}. It expires in 10 minutes.",
        "email_hint": email,
        "demo_otp": code,
        "note": "demo_otp is returned only because email delivery is not configured. In production the code is sent only by email.",
    }


@router.post("/password/change")
def change_password_with_otp(
    payload: PasswordChangeRequest, user: dict = Depends(require_user)
) -> dict:
    """Change password only after a valid OTP sent to the account email."""
    from datetime import datetime, timezone

    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    otp = payload.otp.strip()
    with get_connection() as conn:
        _ensure_otp_table(conn)
        row = conn.execute(
            "SELECT otp_code, expires_at FROM password_otps WHERE user_id = ?",
            (user["id"],),
        ).fetchone()
        if not row:
            raise HTTPException(
                status_code=400,
                detail="No OTP requested. Request a code first.",
            )
        expires_at = row["expires_at"]
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
        except ValueError:
            exp = datetime.now(timezone.utc)
        if datetime.now(timezone.utc) > exp:
            conn.execute("DELETE FROM password_otps WHERE user_id = ?", (user["id"],))
            raise HTTPException(status_code=400, detail="OTP has expired. Request a new code.")
        if row["otp_code"] != otp:
            raise HTTPException(status_code=400, detail="Invalid OTP code")
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.new_password), user["id"]),
        )
        conn.execute("DELETE FROM password_otps WHERE user_id = ?", (user["id"],))
    return {"ok": True, "message": "Password updated successfully."}
