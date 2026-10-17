"""Text preprocessing utilities for normalization and tokenization."""

import re
from typing import Iterable


WORD_RE = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """Lowercase text and collapse whitespace."""
    return " ".join(text.lower().split())


def tokenize(text: str) -> list[str]:
    """Split text into lowercase alphanumeric word tokens."""
    return WORD_RE.findall(normalize(text))


def word_shingles(tokens: list[str], size: int) -> set[str]:
    """Build fixed-size word n-gram shingles from a token list."""
    if not tokens:
        return set()
    if len(tokens) < size:
        return {" ".join(tokens)}
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def char_ngrams(text: str, size: int) -> set[str]:
    """Build character n-grams from normalized text (ignoring spaces)."""
    compact = normalize(text).replace(" ", "")
    if not compact:
        return set()
    if len(compact) < size:
        return {compact}
    return {compact[i : i + size] for i in range(len(compact) - size + 1)}


def term_frequency(tokens: Iterable[str]) -> dict[str, int]:
    """Count how often each token appears."""
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts
