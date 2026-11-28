"""User accounts SQLite (email/password + OAuth profile fields)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from typing import Any

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "plagify.db"


@contextmanager
def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_user_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                name TEXT,
                picture TEXT,
                auth_provider TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS scan_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                scan_date TEXT NOT NULL,
                total_checks INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS login_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT NOT NULL,
                name TEXT,
                event_type TEXT NOT NULL DEFAULT 'login',
                auth_provider TEXT,
                logged_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_reset_token_email ON password_reset_tokens(email);
            CREATE INDEX IF NOT EXISTS idx_reset_token_expires ON password_reset_tokens(expires_at);
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        for col, ddl in [
            ("name", "ALTER TABLE users ADD COLUMN name TEXT"),
            ("picture", "ALTER TABLE users ADD COLUMN picture TEXT"),
            ("auth_provider", "ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'local'"),
            ("phone", "ALTER TABLE users ADD COLUMN phone TEXT"),
            ("institution", "ALTER TABLE users ADD COLUMN institution TEXT"),
            ("role", "ALTER TABLE users ADD COLUMN role TEXT"),
            ("accepted_terms", "ALTER TABLE users ADD COLUMN accepted_terms INTEGER NOT NULL DEFAULT 0"),
        ]:
            if col not in cols:
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass


def record_login_event(
    user_id: int | None,
    email: str,
    name: str | None = None,
    event_type: str = "login",
    auth_provider: str | None = "local",
) -> None:
    """Append a login/register event. Not exposed via the public API."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO login_log (user_id, email, name, event_type, auth_provider, logged_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (user_id, email.lower().strip(), name, event_type, auth_provider or "local"),
        )


def list_login_log(limit: int = 500) -> list[dict[str, Any]]:
    """Return recent login events (for admin CLI only)."""
    init_user_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, email, name, event_type, auth_provider, logged_at
            FROM login_log
            ORDER BY logged_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 5000)),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_or_create_oauth_user(email: str, name: str | None, picture: str | None, provider: str) -> dict:
    email = email.lower().strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, picture, auth_provider FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row:
            new_name = name or row["name"]
            new_picture = picture or row["picture"]
            conn.execute(
                "UPDATE users SET name = ?, picture = ?, auth_provider = ? WHERE id = ?",
                (new_name, new_picture, provider, row["id"]),
            )
            return {
                "id": row["id"],
                "email": row["email"],
                "name": new_name,
                "picture": new_picture,
                "auth_provider": provider,
            }
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, name, picture, auth_provider) VALUES (?, NULL, ?, ?, ?)",
            (email, name, picture, provider),
        )
        return {
            "id": cursor.lastrowid,
            "email": email,
            "name": name,
            "picture": picture,
            "auth_provider": provider,
        }


def record_scan(user_id: int | None = None) -> None:
    today = date.today().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, total_checks FROM scan_stats WHERE scan_date = ? AND user_id IS ?",
            (today, user_id),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE scan_stats SET total_checks = ? WHERE id = ?",
                (row["total_checks"] + 1, row["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO scan_stats (user_id, scan_date, total_checks) VALUES (?, ?, 1)",
                (user_id, today),
            )


def get_statistics(user_id: int | None = None) -> dict:
    today = date.today().isoformat()
    with get_connection() as conn:
        total_checks = conn.execute(
            "SELECT COALESCE(SUM(total_checks), 0) AS total FROM scan_stats WHERE user_id IS ?",
            (user_id,),
        ).fetchone()["total"]
        today_row = conn.execute(
            "SELECT total_checks FROM scan_stats WHERE scan_date = ? AND user_id IS ?",
            (today, user_id),
        ).fetchone()
        documents_today = today_row["total_checks"] if today_row else 0
    return {"total_checks": total_checks, "documents_scanned_today": documents_today}


# Password reset token functions (database-backed for serverless compatibility)

import secrets
from datetime import datetime, timedelta, timezone


def create_reset_token(email: str) -> str:
    """Create a secure password reset token stored in database."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO password_reset_tokens (token, email, expires_at, used)
            VALUES (?, ?, ?, 0)
            """,
            (token, email.lower(), expires_at.isoformat()),
        )
    return token


def verify_reset_token(token: str) -> str | None:
    """Verify a password reset token and return the email if valid."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT email, expires_at, used FROM password_reset_tokens WHERE token = ?
            """,
            (token,),
        ).fetchone()
    
    if not row:
        return None
    if row["used"]:
        return None
    if datetime.now(timezone.utc) > datetime.fromisoformat(row["expires_at"]):
        # Clean up expired token
        with get_connection() as conn:
            conn.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))
        return None
    return row["email"]


def mark_token_used(token: str) -> None:
    """Mark a reset token as used."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
            (token,),
        )


def cleanup_expired_tokens() -> int:
    """Remove expired tokens. Returns count of deleted tokens."""
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM password_reset_tokens WHERE expires_at < ?",
            (datetime.now(timezone.utc).isoformat(),),
        )
        return cur.rowcount
