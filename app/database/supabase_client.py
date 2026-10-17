"""Supabase client for original reference documents.

Uses service-role key server-side only. Falls back to local SQLite storage
when SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not configured.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import (
    DATA_DIR,
    SUPABASE_BUCKET,
    SUPABASE_ENABLED,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_URL,
)

logger = logging.getLogger(__name__)


def supabase_status() -> dict[str, Any]:
    return {
        "enabled": SUPABASE_ENABLED,
        "bucket": SUPABASE_BUCKET if SUPABASE_ENABLED else None,
        "mode": "supabase" if SUPABASE_ENABLED else "local_sqlite",
        "message": (
            "Supabase is configured."
            if SUPABASE_ENABLED
            else "Supabase is not configured. Original documents are stored locally in SQLite. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable Supabase Storage."
        ),
    }


def _get_client():
    if not SUPABASE_ENABLED:
        return None
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "supabase package is not installed. Run: pip install supabase"
        ) from exc
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def upload_original_file(owner_id: str, filename: str, content: bytes) -> str:
    """Upload bytes to private bucket; return storage path."""
    client = _get_client()
    if client is None:
        raise RuntimeError("Supabase is not configured")
    safe_name = filename.replace("/", "_").replace("\\", "_")
    path = f"{owner_id}/{uuid.uuid4().hex}_{safe_name}"
    client.storage.from_(SUPABASE_BUCKET).upload(
        path,
        content,
        file_options={"content-type": "application/octet-stream", "upsert": "false"},
    )
    return path


def delete_storage_object(path: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.storage.from_(SUPABASE_BUCKET).remove([path])
    except Exception as exc:
        logger.warning("Failed to delete storage object %s: %s", path, exc)


def insert_original_row(row: dict[str, Any]) -> dict[str, Any]:
    client = _get_client()
    if client is None:
        raise RuntimeError("Supabase is not configured")
    result = client.table("original_documents").insert(row).execute()
    data = result.data
    return data[0] if data else row


def get_original_row(owner_id: str) -> dict[str, Any] | None:
    client = _get_client()
    if client is None:
        return None
    result = (
        client.table("original_documents")
        .select("*")
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def delete_original_row(owner_id: str, doc_id: str) -> bool:
    client = _get_client()
    if client is None:
        return False
    client.table("original_documents").delete().eq("id", doc_id).eq(
        "owner_id", owner_id
    ).execute()
    return True
