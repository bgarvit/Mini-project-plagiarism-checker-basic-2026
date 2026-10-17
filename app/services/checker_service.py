"""Plagiarism scanning service built on the checker package."""

import re
from dataclasses import dataclass

from checker import DocumentStore, compare_with_document, find_matching_phrases

from ..config import DEFAULT_THRESHOLD, DEFAULT_TOP_SOURCES, DOCUMENTS_DIR
from .ai_detector import estimate_ai_likelihood

QUOTE_RE = re.compile(r'"([^"]{20,})"|“([^”]{20,})”|‘([^’]{20,})’')
BIBLIO_RE = re.compile(
    r"(?mi)^(?:references|bibliography|works cited|sources)\s*$.*",
    re.DOTALL,
)


@dataclass
class SourceMatch:
    doc_id: str
    title: str
    similarity: float
    scores: dict[str, float]
    phrases: list[str]


@dataclass
class ScanResult:
    unique_percent: float
    similarity_percent: float
    sources_found: int
    words_scanned: int
    sources: list[SourceMatch]
    ai_likelihood: float | None
    scan_mode: str


class CheckerService:
    def __init__(self, docs_dir=DOCUMENTS_DIR) -> None:
        self.store = DocumentStore(docs_dir)
        self.store.load()

    def reload_documents(self) -> int:
        return self.store.load()

    def preprocess(
        self,
        text: str,
        exclude_quotes: bool = False,
        exclude_bibliography: bool = False,
    ) -> str:
        cleaned = text.strip()
        if exclude_bibliography:
            cleaned = BIBLIO_RE.sub("", cleaned).strip()
        if exclude_quotes:
            cleaned = QUOTE_RE.sub("", cleaned).strip()
        return cleaned

    def scan(
        self,
        text: str,
        *,
        threshold: float = DEFAULT_THRESHOLD,
        top: int = DEFAULT_TOP_SOURCES,
        exclude_quotes: bool = False,
        exclude_bibliography: bool = False,
        detect_ai: bool = True,
        fingerprint_matching: bool = True,
        scan_mode: str = "normal",
        phrase_min: int = 20,
    ) -> ScanResult:
        cleaned = self.preprocess(text, exclude_quotes, exclude_bibliography)
        words = cleaned.split()
        if len(words) < 5:
            raise ValueError("Please provide at least 5 words to scan")

        mode_threshold = {
            "normal": threshold,
            "deep": max(threshold - 0.05, 0.05),
            "academic": max(threshold - 0.03, 0.08),
        }.get(scan_mode, threshold)

        matches: list[SourceMatch] = []
        for document in self.store.list_documents():
            report = compare_with_document(cleaned, document.content)
            if report.overall >= mode_threshold:
                phrases = []
                if fingerprint_matching and len(cleaned) <= 8000:
                    phrases = find_matching_phrases(cleaned, document.content, min_length=phrase_min)[:5]
                matches.append(
                    SourceMatch(
                        doc_id=document.doc_id,
                        title=document.title,
                        similarity=round(report.overall, 4),
                        scores=report.as_dict(),
                        phrases=phrases,
                    )
                )

        matches.sort(key=lambda item: item.similarity, reverse=True)
        matches = matches[:top]

        highest_similarity = matches[0].similarity if matches else 0.0
        similarity_percent = round(highest_similarity * 100, 2)
        unique_percent = round(max(100.0 - similarity_percent, 0.0), 2)

        ai_score = estimate_ai_likelihood(cleaned) if detect_ai else None

        return ScanResult(
            unique_percent=unique_percent,
            similarity_percent=similarity_percent,
            sources_found=len(matches),
            words_scanned=len(words),
            sources=matches,
            ai_likelihood=ai_score,
            scan_mode=scan_mode,
        )

    def list_documents(self) -> list[dict]:
        return [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "word_count": len(doc.content.split()),
            }
            for doc in self.store.list_documents()
        ]

    def add_document(self, doc_id: str, content: str, title: str | None = None) -> dict:
        document = self.store.add_text(doc_id, content, title=title)
        return {
            "doc_id": document.doc_id,
            "title": document.title,
            "word_count": len(document.content.split()),
        }

    def result_to_dict(self, result: ScanResult) -> dict:
        return {
            "unique_percent": result.unique_percent,
            "similarity_percent": result.similarity_percent,
            "sources_found": result.sources_found,
            "words_scanned": result.words_scanned,
            "ai_likelihood": result.ai_likelihood,
            "scan_mode": result.scan_mode,
            "sources": [
                {
                    "doc_id": source.doc_id,
                    "title": source.title,
                    "similarity": source.similarity,
                    "similarity_percent": round(source.similarity * 100, 2),
                    "scores": source.scores,
                    "phrases": source.phrases,
                }
                for source in result.sources
            ],
        }
