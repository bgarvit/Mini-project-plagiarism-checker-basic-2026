"""Document validation and text extraction (TXT, PDF, DOCX)."""

from __future__ import annotations

import hashlib
import logging
import re
from io import BytesIO
from pathlib import Path

from app.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, MIN_TEXT_CHARS

logger = logging.getLogger(__name__)

_WS_RE = re.compile(r"[ \t]+")
_NL_RE = re.compile(r"\n{3,}")


def validate_upload(filename: str | None, content: bytes) -> str:
    if not content:
        raise ValueError("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit")
    name = filename or "upload.txt"
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{suffix or 'unknown'}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    # Basic magic-byte checks (content, not just extension)
    if suffix == ".pdf" and not content[:5].startswith(b"%PDF"):
        raise ValueError("File extension is .pdf but content is not a valid PDF")
    if suffix == ".docx" and not content[:2] == b"PK":
        raise ValueError("File extension is .docx but content is not a valid ZIP/DOCX")
    return name


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        text = _decode_text(content)
    elif suffix == ".pdf":
        text = _extract_pdf(content)
    elif suffix in {".docx", ".doc"}:
        text = _extract_docx(content)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    text = normalize_text(text)
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise ValueError(
            f"Extracted text is too short (minimum {MIN_TEXT_CHARS} characters). "
            "The file may be empty, image-only, or unreadable."
        )
    return text


def _decode_text(content: bytes) -> str:
    """Decode text content handling various encodings properly."""
    # Check for UTF-16 BOM (LE or BE) - DO NOT strip null bytes for UTF-16
    if content.startswith(b"\xff\xfe"):
        try:
            return content.decode("utf-16-le", errors="ignore")
        except UnicodeDecodeError:
            pass
    elif content.startswith(b"\xfe\xff"):
        try:
            return content.decode("utf-16-be", errors="ignore")
        except UnicodeDecodeError:
            pass
    
    # Check for UTF-8 BOM
    if content.startswith(b"\xef\xbb\xbf"):
        try:
            return content.decode("utf-8", errors="ignore")
        except UnicodeDecodeError:
            pass
    
    # Try UTF-8
    try:
        return content.decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        # Fallback to latin-1
        return content.decode("latin-1", errors="ignore")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _extract_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text)
