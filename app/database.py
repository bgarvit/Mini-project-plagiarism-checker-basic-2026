"""SQLite helpers for users and scan statistics."""

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from .config import DATA_DIR

DB_PATH = DATA_DIR / "plagify.db"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
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
            """
        )
        # Migrate older DBs that only had email + password_hash
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "name" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT")
        if "picture" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN picture TEXT")
        if "auth_provider" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'local'")
        # Allow NULL password_hash for OAuth-only users on older schemas
        # SQLite cannot easily drop NOT NULL; new installs already allow NULL.


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


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
    return {
        "total_checks": total_checks,
        "documents_scanned_today": documents_today,
    }


def get_or_create_oauth_user(email: str, name: str | None, picture: str | None, provider: str) -> dict:
    email = email.lower().strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, picture, auth_provider FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row:
            # Refresh profile fields if provided
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
