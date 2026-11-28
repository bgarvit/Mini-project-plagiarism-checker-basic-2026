"""Local SQLite persistence for original reference documents (Supabase fallback)."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "plagify.db"


@contextmanager
def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_original_table() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS original_documents (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                storage_path TEXT,
                extracted_text TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_orig_owner ON original_documents(owner_id);
            """
        )


def save_original(
    owner_id: str,
    document_name: str,
    extracted_text: str,
    content_hash: str,
    storage_path: str | None = None,
) -> dict[str, Any]:
    """Save a new original document. Previous files are kept in history;
    the latest remains the active comparison target.
    """
    init_original_table()
    doc_id = str(uuid.uuid4())
    created = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO original_documents
            (id, owner_id, document_name, storage_path, extracted_text, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, owner_id, document_name, storage_path, extracted_text, content_hash, created),
        )
    return {
        "id": doc_id,
        "owner_id": owner_id,
        "document_name": document_name,
        "storage_path": storage_path,
        "content_hash": content_hash,
        "created_at": created,
        "has_text": True,
    }


def get_original(owner_id: str) -> dict[str, Any] | None:
    """Return the latest original for comparison."""
    init_original_table()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM original_documents WHERE owner_id = ? ORDER BY created_at DESC LIMIT 1",
            (owner_id,),
        ).fetchone()
    if not row:
        return None
    return dict(row)


def list_originals(owner_id: str) -> list[dict[str, Any]]:
    """List all saved original documents for an owner (metadata only)."""
    init_original_table()
    with _conn() as c:
        rows = c.execute(
            """
            SELECT id, owner_id, document_name, storage_path, content_hash, created_at,
                   LENGTH(extracted_text) AS text_length
            FROM original_documents
            WHERE owner_id = ?
            ORDER BY created_at DESC
            """,
            (owner_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_original(owner_id: str) -> bool:
    init_original_table()
    with _conn() as c:
        cur = c.execute("DELETE FROM original_documents WHERE owner_id = ?", (owner_id,))
        return cur.rowcount > 0


def metadata_only(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "owner_id": row.get("owner_id"),
        "document_name": row.get("document_name"),
        "storage_path": row.get("storage_path"),
        "content_hash": row.get("content_hash"),
        "created_at": row.get("created_at"),
        "has_text": bool(row.get("extracted_text")),
    }
