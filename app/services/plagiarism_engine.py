"""Document-to-document plagiarism comparison against a single original reference.

Does NOT search the internet or other users' documents.
Similarity is measured only against the registered original.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from checker.preprocess import tokenize

_SENT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class MatchPassage:
    submitted: str
    original: str
    similarity: float
    match_type: str  # exact | approximate


def _sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENT_RE.split(text) if s.strip()]
    # Also split long paragraphs without punctuation
    out: list[str] = []
    for p in parts:
        if len(p) > 400:
            chunks = re.split(r"\n+", p)
            out.extend(c.strip() for c in chunks if c.strip())
        else:
            out.append(p)
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _shingle(tokens: list[str], n: int = 3) -> set[str]:
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def compare_documents(original_text: str, submitted_text: str) -> dict[str, Any]:
    """Compare submitted text against original only.

    Scoring:
    - Token Jaccard overlap on full documents (weight 0.4)
    - 3-gram shingle Jaccard (weight 0.4)
    - Average best sentence-level matches (weight 0.2)
    Overall similarity is 0–100%.
    """
    orig = (original_text or "").strip()
    sub = (submitted_text or "").strip()
    if not orig or not sub:
        raise ValueError("Both original and submitted text are required")

    orig_tokens = tokenize(orig)
    sub_tokens = tokenize(sub)
    token_sim = _jaccard(set(orig_tokens), set(sub_tokens))
    shingle_sim = _jaccard(_shingle(orig_tokens, 3), _shingle(sub_tokens, 3))

    orig_sents = _sentences(orig)
    sub_sents = _sentences(sub)
    matches: list[MatchPassage] = []
    best_scores: list[float] = []

    for s in sub_sents:
        s_tok = set(tokenize(s))
        if len(s_tok) < 4:
            continue
        best = 0.0
        best_o = ""
        for o in orig_sents:
            o_tok = set(tokenize(o))
            if len(o_tok) < 4:
                continue
            sc = _jaccard(s_tok, o_tok)
            if sc > best:
                best = sc
                best_o = o
        if best >= 0.55:
            best_scores.append(best)
            matches.append(
                MatchPassage(
                    submitted=s[:500],
                    original=best_o[:500],
                    similarity=round(best, 4),
                    match_type="exact" if best >= 0.92 else "approximate",
                )
            )
        elif best >= 0.35:
            best_scores.append(best)

    sent_avg = sum(best_scores) / len(best_scores) if best_scores else 0.0
    overall = token_sim * 0.4 + shingle_sim * 0.4 + sent_avg * 0.2
    overall_pct = round(min(max(overall * 100, 0), 100), 2)

    # Sort matches by similarity desc, cap list
    matches.sort(key=lambda m: m.similarity, reverse=True)
    match_dicts = [
        {
            "submitted": m.submitted,
            "original": m.original,
            "similarity": m.similarity,
            "match_type": m.match_type,
        }
        for m in matches[:40]
    ]

    return {
        "similarity_percent": overall_pct,
        "token_overlap": round(token_sim * 100, 2),
        "shingle_overlap": round(shingle_sim * 100, 2),
        "sentence_match_avg": round(sent_avg * 100, 2),
        "matched_passage_count": len(match_dicts),
        "matched_passages": match_dicts,
        "submitted_word_count": len(sub_tokens),
        "original_word_count": len(orig_tokens),
        "scoring_method": (
            "Weighted combination of token Jaccard (40%), 3-gram shingle Jaccard (40%), "
            "and average best sentence-level Jaccard matches (20%). "
            "This measures similarity to the registered original document only — "
            "not plagiarism against the internet."
        ),
        "disclaimer": (
            "A high similarity percentage indicates textual overlap with the registered "
            "original reference. It is not proof of intentional plagiarism and does not "
            "search external sources."
        ),
    }
