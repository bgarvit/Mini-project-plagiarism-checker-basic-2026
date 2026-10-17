"""AI-content detection — real providers only; never fabricates success.

Provider priority when AI_DETECTION_PROVIDER=auto:
  1. lmscan (local, offline, no API key) if installed
  2. GPTZero API if GPTZERO_API_KEY is set
  3. Sapling API if SAPLING_API_KEY is set
  4. Built-in statistical heuristic (always available, clearly labeled)

Results always include provider name and a limitations warning.
"""

from __future__ import annotations

import logging
import re
from statistics import pstdev
from typing import Any

import httpx

from app.config import (
    AI_DETECTION_PROVIDER,
    GPTZERO_API_KEY,
    MAX_TEXT_CHARS,
    MIN_TEXT_CHARS,
    SAPLING_API_KEY,
)

logger = logging.getLogger(__name__)

LIMITATIONS = (
    "AI detection is probabilistic and can produce false positives and false negatives. "
    "Scores are signals to inform judgment — not proof that text was or was not written by AI. "
    "Formal, heavily edited, or non-native writing is more often misclassified."
)

AI_PHRASES = (
    "it is important to note",
    "in today's world",
    "in conclusion",
    "furthermore",
    "moreover",
    "additionally",
    "as an ai",
    "delve into",
    "tapestry",
    "multifaceted",
    "leverage",
    "utilize",
    "in today's rapidly evolving",
    "it is worth noting",
    "plays a crucial role",
)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class AIDetectionError(Exception):
    """Raised when detection cannot be completed honestly."""


def _chunk_text(text: str, max_chars: int = 12_000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # Prefer break at paragraph
            br = text.rfind("\n\n", start, end)
            if br > start + max_chars // 2:
                end = br
        chunks.append(text[start:end])
        start = end
    return chunks


def _heuristic_score(text: str) -> dict[str, Any]:
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if len(tokens) < 30:
        return {
            "ai_probability": 0.0,
            "verdict": "insufficient_text",
            "confidence": "low",
            "details": {"reason": "Fewer than 30 tokens"},
        }

    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    sentence_lengths = [len(re.findall(r"[a-zA-Z']+", s)) for s in sentences] or [0]
    avg_len = sum(sentence_lengths) / max(len(sentence_lengths), 1)
    length_uniformity = 1.0 - min(
        (pstdev(sentence_lengths) if len(sentence_lengths) > 1 else 0) / max(avg_len, 1), 1.0
    )
    unique_ratio = len(set(tokens)) / len(tokens)
    low_diversity = max(0.0, 0.65 - unique_ratio) / 0.65
    lowered = text.lower()
    phrase_hits = sum(1 for p in AI_PHRASES if p in lowered)
    phrase_score = min(phrase_hits / 4, 1.0)
    transitions = sum(
        1 for t in tokens if t in {"however", "therefore", "thus", "hence", "moreover", "furthermore"}
    )
    transition_score = min(transitions / max(len(sentences), 1) / 0.35, 1.0)
    score = (
        length_uniformity * 0.30
        + low_diversity * 0.25
        + phrase_score * 0.30
        + transition_score * 0.15
    )
    score = round(min(max(score, 0.0), 1.0), 4)
    if score >= 0.65:
        verdict = "likely_ai"
    elif score >= 0.4:
        verdict = "mixed_or_uncertain"
    else:
        verdict = "likely_human"
    confidence = "low" if abs(score - 0.5) < 0.15 else "medium"
    return {
        "ai_probability": score,
        "verdict": verdict,
        "confidence": confidence,
        "details": {
            "phrase_hits": phrase_hits,
            "unique_token_ratio": round(unique_ratio, 3),
            "sentence_count": len(sentences),
        },
    }


def _try_lmscan(text: str) -> dict[str, Any] | None:
    try:
        from lmscan import scan  # type: ignore
    except ImportError:
        return None
    try:
        result = scan(text)
        ai_prob = float(getattr(result, "ai_probability", None) or result.get("ai_probability", 0))
        verdict_raw = str(getattr(result, "verdict", None) or result.get("verdict", "")).lower()
        conf = str(getattr(result, "confidence", None) or result.get("confidence", "medium"))
        if ai_prob >= 0.65:
            verdict = "likely_ai"
        elif ai_prob >= 0.4:
            verdict = "mixed_or_uncertain"
        else:
            verdict = "likely_human"
        if "ai" in verdict_raw and "human" not in verdict_raw:
            verdict = "likely_ai"
        return {
            "ai_probability": round(ai_prob, 4),
            "verdict": verdict,
            "confidence": conf,
            "details": {"engine": "lmscan", "raw_verdict": verdict_raw},
            "provider": "lmscan",
        }
    except Exception as exc:
        logger.warning("lmscan failed: %s", exc)
        return None


async def _try_gptzero(text: str) -> dict[str, Any] | None:
    if not GPTZERO_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.gptzero.me/v2/predict/text",
                headers={
                    "x-api-key": GPTZERO_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={"document": text[:MAX_TEXT_CHARS]},
            )
        if resp.status_code != 200:
            logger.warning("GPTZero HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        data = resp.json()
        # Schema varies; handle common fields
        doc = data.get("documents", [data])[0] if isinstance(data, dict) else {}
        ai_prob = doc.get("completely_generated_prob") or doc.get("average_generated_prob")
        if ai_prob is None and "class_probabilities" in doc:
            probs = doc["class_probabilities"]
            ai_prob = probs.get("ai") or probs.get("AI") or 0
        if ai_prob is None:
            return None
        ai_prob = float(ai_prob)
        if ai_prob >= 0.65:
            verdict = "likely_ai"
        elif ai_prob >= 0.4:
            verdict = "mixed_or_uncertain"
        else:
            verdict = "likely_human"
        return {
            "ai_probability": round(ai_prob, 4),
            "verdict": verdict,
            "confidence": "medium",
            "details": {"engine": "gptzero"},
            "provider": "gptzero",
        }
    except Exception as exc:
        logger.warning("GPTZero request failed: %s", exc)
        return None


async def _try_sapling(text: str) -> dict[str, Any] | None:
    if not SAPLING_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.sapling.ai/api/v1/aidetect",
                json={"key": SAPLING_API_KEY, "text": text[:MAX_TEXT_CHARS]},
            )
        if resp.status_code != 200:
            logger.warning("Sapling HTTP %s: %s", resp.status_code, resp.text[:300])
            return None
        data = resp.json()
        score = data.get("score")
        if score is None:
            return None
        ai_prob = float(score)
        if ai_prob >= 0.65:
            verdict = "likely_ai"
        elif ai_prob >= 0.4:
            verdict = "mixed_or_uncertain"
        else:
            verdict = "likely_human"
        return {
            "ai_probability": round(ai_prob, 4),
            "verdict": verdict,
            "confidence": "medium",
            "details": {"engine": "sapling"},
            "provider": "sapling",
        }
    except Exception as exc:
        logger.warning("Sapling request failed: %s", exc)
        return None


async def analyze_text(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if len(text) < MIN_TEXT_CHARS:
        raise AIDetectionError(
            f"Text too short for reliable detection (minimum {MIN_TEXT_CHARS} characters)."
        )
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]

    provider_pref = AI_DETECTION_PROVIDER
    result: dict[str, Any] | None = None

    async def run_auto() -> dict[str, Any] | None:
        r = _try_lmscan(text)
        if r:
            return r
        r = await _try_gptzero(text)
        if r:
            return r
        r = await _try_sapling(text)
        if r:
            return r
        return None

    if provider_pref == "lmscan":
        result = _try_lmscan(text)
        if not result:
            raise AIDetectionError(
                "lmscan is not installed. Run: pip install lmscan  "
                "Or set AI_DETECTION_PROVIDER=auto / gptzero / sapling / heuristic."
            )
    elif provider_pref == "gptzero":
        result = await _try_gptzero(text)
        if not result:
            raise AIDetectionError(
                "GPTZero detection failed. Set GPTZERO_API_KEY or switch provider."
            )
    elif provider_pref == "sapling":
        result = await _try_sapling(text)
        if not result:
            raise AIDetectionError(
                "Sapling detection failed. Set SAPLING_API_KEY or switch provider."
            )
    elif provider_pref == "heuristic":
        result = _heuristic_score(text)
        result["provider"] = "heuristic"
    else:
        # auto
        result = await run_auto()
        if not result:
            result = _heuristic_score(text)
            result["provider"] = "heuristic"

    result["limitations"] = LIMITATIONS
    result["text_length"] = len(text)
    result["word_count"] = len(re.findall(r"\S+", text))
    return result
