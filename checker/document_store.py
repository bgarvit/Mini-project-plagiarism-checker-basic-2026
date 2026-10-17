"""Load and manage reference documents for comparison."""

from dataclasses import dataclass
from pathlib import Path


TEXT_EXTENSIONS = {".txt", ".md", ".text"}


def read_text_file(path: Path) -> str:
    """Read a text file, handling UTF-8 and UTF-16 encodings."""
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if b"\x00" in raw[: min(len(raw), 100)]:
        return raw.decode("utf-16-le", errors="ignore")
    return raw.decode("utf-8", errors="ignore")


@dataclass(frozen=True)
class StoredDocument:
    doc_id: str
    title: str
    path: Path
    content: str


class DocumentStore:
    """In-memory collection of reference documents loaded from disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.documents: dict[str, StoredDocument] = {}

    def load(self) -> int:
        """Load all supported text files from the store directory."""
        self.documents.clear()
        if not self.root.exists():
            self.root.mkdir(parents=True, exist_ok=True)
            return 0

        count = 0
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            content = read_text_file(path)
            doc_id = path.stem
            self.documents[doc_id] = StoredDocument(
                doc_id=doc_id,
                title=path.name,
                path=path,
                content=content,
            )
            count += 1
        return count

    def add_text(self, doc_id: str, content: str, title: str | None = None) -> StoredDocument:
        """Add or replace a document in memory and persist it to disk."""
        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"{doc_id}.txt"
        path = self.root / filename
        path.write_text(content, encoding="utf-8")
        document = StoredDocument(
            doc_id=doc_id,
            title=title or filename,
            path=path,
            content=content,
        )
        self.documents[doc_id] = document
        return document

    def get(self, doc_id: str) -> StoredDocument | None:
        return self.documents.get(doc_id)

    def list_documents(self) -> list[StoredDocument]:
        return sorted(self.documents.values(), key=lambda doc: doc.title)
