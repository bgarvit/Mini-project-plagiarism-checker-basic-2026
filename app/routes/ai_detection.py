"""AI detection API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.auth_utils import get_current_user
from app.config import MAX_TEXT_CHARS, MIN_TEXT_CHARS
from app.services.ai_detector import AIDetectionError, analyze_text
from app.services.document_processor import extract_text, validate_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-detection", tags=["ai-detection"])


class TextAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)


@router.post("/analyze")
async def analyze(
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    user: dict | None = Depends(get_current_user),
) -> dict:
    """Analyze pasted text or an uploaded document for AI-generated content."""
    body_text = (text or "").strip()

    if file is not None and file.filename:
        content = await file.read()
        try:
            name = validate_upload(file.filename, content)
            body_text = extract_text(name, content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            # Do not retain upload bytes beyond this request
            del content

    if not body_text:
        raise HTTPException(
            status_code=400,
            detail="Provide text or upload a TXT/PDF/DOCX file.",
        )
    if len(body_text) < MIN_TEXT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Text too short (minimum {MIN_TEXT_CHARS} characters).",
        )
    if len(body_text) > MAX_TEXT_CHARS:
        body_text = body_text[:MAX_TEXT_CHARS]

    try:
        result = await analyze_text(body_text)
    except AIDetectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("AI detection failed")
        raise HTTPException(
            status_code=503,
            detail=f"AI detection service error: {exc}",
        ) from exc

    result["authenticated"] = user is not None
    return result


@router.post("/analyze-json")
async def analyze_json(
    payload: TextAnalyzeRequest,
    user: dict | None = Depends(get_current_user),
) -> dict:
    try:
        result = await analyze_text(payload.text)
    except AIDetectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result["authenticated"] = user is not None
    return result
