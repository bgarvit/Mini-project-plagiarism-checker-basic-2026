"""Basic plagiarism checker package."""

from .algorithms import SimilarityReport, compare_texts, compare_with_document, find_matching_phrases
from .document_store import DocumentStore, StoredDocument

__all__ = [
    "DocumentStore",
    "SimilarityReport",
    "StoredDocument",
    "compare_texts",
    "compare_with_document",
    "find_matching_phrases",
]
