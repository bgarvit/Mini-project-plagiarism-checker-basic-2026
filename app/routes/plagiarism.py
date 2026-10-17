"""Original-document plagiarism API (compare against registered original only)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth_utils import get_current_user, require_user
from app.config import SUPABASE_ENABLED
from app.database import original_store
from app.database.supabase_client import (
    delete_storage_object,
    get_original_row,
    insert_original_row,
    supabase_status,
    upload_original_file,
)
from app.services.document_processor import content_hash, extract_text, validate_upload
from app.services.plagiarism_engine import compare_documents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/plagiarism", tags=["plagiarism"])


def _owner_id(user: dict) -> str:
    return str(user["id"])


@router.get("/status")
def storage_status(user: dict | None = Depends(get_current_user)) -> dict:
    return supabase_status()


@router.get("/original")
def get_original(user: dict = Depends(require_user)) -> dict:
    owner = _owner_id(user)
    if SUPABASE_ENABLED:
        row = get_original_row(owner)
        if row:
            # Do not return full extracted text to client by default
            return {
                "registered": True,
                "document": {
                    "id": row.get("id"),
                    "document_name": row.get("document_name"),
                    "content_hash": row.get("content_hash"),
                    "created_at": row.get("created_at"),
                    "storage_path": row.get("storage_path"),
                },
                "storage": "supabase",
            }
        return {"registered": False, "document": None, "storage": "supabase"}

    row = original_store.get_original(owner)
    meta = original_store.metadata_only(row)
    return {
        "registered": meta is not None,
        "document": meta,
        "storage": "local_sqlite",
    }


@router.post("/original")
async def register_original(
    file: UploadFile = File(...),
    user: dict = Depends(require_user),
) -> dict:
    """Register (or replace) the owner's original reference document."""
    content = await file.read()
    tmp_path: Path | None = None
    try:
        name = validate_upload(file.filename, content)
        text = extract_text(name, content)
        digest = content_hash(content)
        owner = _owner_id(user)
        storage_path = None

        if SUPABASE_ENABLED:
            # Remove previous original for this owner
            prev = get_original_row(owner)
            if prev and prev.get("storage_path"):
                delete_storage_object(prev["storage_path"])
            if prev and prev.get("id"):
                from app.database.supabase_client import delete_original_row

                delete_original_row(owner, str(prev["id"]))

            storage_path = upload_original_file(owner, name, content)
            row = {
                "owner_id": owner,
                "document_name": name,
                "storage_path": storage_path,
                "extracted_text": text,
                "content_hash": digest,
            }
            saved = insert_original_row(row)
            return {
                "ok": True,
                "document": {
                    "id": saved.get("id"),
                    "document_name": name,
                    "content_hash": digest,
                    "created_at": saved.get("created_at"),
                    "storage_path": storage_path,
                },
                "storage": "supabase",
                "message": "Original reference document registered in Supabase.",
            }

        saved = original_store.save_original(
            owner_id=owner,
            document_name=name,
            extracted_text=text,
            content_hash=digest,
            storage_path=None,
        )
        return {
            "ok": True,
            "document": original_store.metadata_only(saved),
            "storage": "local_sqlite",
            "message": (
                "Original reference document registered locally. "
                "Configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY for Supabase Storage."
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to register original")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Never keep the uploaded bytes after processing
        del content
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.delete("/original")
def delete_original(user: dict = Depends(require_user)) -> dict:
    owner = _owner_id(user)
    if SUPABASE_ENABLED:
        row = get_original_row(owner)
        if not row:
            raise HTTPException(status_code=404, detail="No original document registered")
        if row.get("storage_path"):
            delete_storage_object(row["storage_path"])
        from app.database.supabase_client import delete_original_row

        delete_original_row(owner, str(row["id"]))
        return {"ok": True, "message": "Original document deleted"}
    if not original_store.delete_original(owner):
        raise HTTPException(status_code=404, detail="No original document registered")
    return {"ok": True, "message": "Original document deleted"}


@router.post("/compare")
async def compare(
    file: UploadFile = File(...),
    user: dict = Depends(require_user),
) -> dict:
    """Compare a temporary submitted document against the stored original.

    The submitted file is processed in memory only and is not saved.
    """
    content = await file.read()
    try:
        name = validate_upload(file.filename, content)
        submitted_text = extract_text(name, content)
        owner = _owner_id(user)

        original_text = None
        original_meta = None

        if SUPABASE_ENABLED:
            row = get_original_row(owner)
            if not row or not row.get("extracted_text"):
                raise HTTPException(
                    status_code=400,
                    detail="No original document registered. Upload one first via POST /api/plagiarism/original.",
                )
            original_text = row["extracted_text"]
            original_meta = {
                "id": row.get("id"),
                "document_name": row.get("document_name"),
                "content_hash": row.get("content_hash"),
            }
        else:
            row = original_store.get_original(owner)
            if not row or not row.get("extracted_text"):
                raise HTTPException(
                    status_code=400,
                    detail="No original document registered. Upload one first.",
                )
            original_text = row["extracted_text"]
            original_meta = original_store.metadata_only(row)

        result = compare_documents(original_text, submitted_text)
        result["submitted_filename"] = name
        result["original"] = original_meta
        result["storage"] = "supabase" if SUPABASE_ENABLED else "local_sqlite"
        return result
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Compare failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Explicitly drop submitted content; never persist
        del content
