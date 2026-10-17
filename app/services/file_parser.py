"""Extract plain text from uploaded documents."""

from io import BytesIO
from pathlib import Path


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        return _extract_pdf(content)
    if suffix in {".docx", ".doc"}:
        return _extract_docx(content)
    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    if not parts:
        raise ValueError("Could not extract text from PDF")
    return "\n\n".join(parts)


def _extract_docx(content: bytes) -> str:
    from docx import Document

    document = Document(BytesIO(content))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    if not parts:
        raise ValueError("Could not extract text from document")
    return "\n\n".join(parts)
