"""Unit tests for document-to-document comparison."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.plagiarism_engine import compare_documents


def test_identical_texts_high_similarity():
    text = "The quick brown fox jumps over the lazy dog. Science requires careful observation and analysis of experimental data."
    result = compare_documents(text, text)
    assert result["similarity_percent"] >= 90


def test_unrelated_texts_low_similarity():
    a = "Quantum entanglement connects particles across space in ways classical physics cannot explain."
    b = "A recipe for chocolate cake uses flour, sugar, cocoa, eggs, and butter mixed carefully."
    result = compare_documents(a, b)
    assert result["similarity_percent"] < 40


def test_partial_overlap_finds_passages():
    original = (
        "Climate change affects coastal cities through rising sea levels. "
        "Renewable energy sources include solar and wind power generation systems."
    )
    submitted = (
        "Climate change affects coastal cities through rising sea levels. "
        "Meanwhile, local markets sell seasonal fruit every weekend."
    )
    result = compare_documents(original, submitted)
    assert result["matched_passage_count"] >= 1
    assert "scoring_method" in result
