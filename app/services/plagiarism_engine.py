"""Advanced Document-to-Document Plagiarism Detection Engine.

Uses TF-IDF + Cosine Similarity as primary algorithm, supplemented by
Jaccard similarity and n-gram overlap for robust detection.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from app.services.preprocess import (
    tokenize,
    tokenize_raw,
    sentence_tokenize,
    word_shingles,
    char_ngrams,
    preprocess_for_tfidf,
    preprocess_for_matching,
    NLTK_AVAILABLE,
)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class MatchPassage:
    submitted: str
    original: str
    similarity: float
    match_type: str  # exact | high | moderate | paraphrased
    match_algorithm: str  # tfidf_cosine | jaccard | shingle | char_ngram


_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _jaccard(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _cosine_sim(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors (dict)."""
    if not vec_a or not vec_b:
        return 0.0
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    if not common_keys:
        return 0.0
    dot_product = sum(vec_a[k] * vec_b[k] for k in common_keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _tfidf_vectorize(texts: list[str], max_features: int = 10000) -> tuple[np.ndarray, list[str]]:
    """
    Compute TF-IDF vectors for a list of texts.
    Returns (matrix, feature_names).
    """
    if SKLEARN_AVAILABLE:
        vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=(1, 2),  # unigrams + bigrams
            sublinear_tf=True,
            min_df=1,
            max_df=1.0,  # Don't filter high-frequency terms
            token_pattern=r'(?u)\b[a-z0-9]+\b',
            lowercase=True,
            stop_words=None,  # We handle stopwords in preprocessing
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
        return tfidf_matrix.toarray(), vectorizer.get_feature_names_out().tolist()
    
    # Fallback: Manual TF-IDF implementation
    return _manual_tfidf(texts, max_features)


def _manual_tfidf(texts: list[str], max_features: int) -> tuple[np.ndarray, list[str]]:
    """Manual TF-IDF implementation when sklearn unavailable."""
    # Tokenize all documents
    all_tokens = [tokenize_raw(t) for t in texts]
    
    # Build vocabulary
    doc_freq: dict[str, int] = {}
    for tokens in all_tokens:
        unique_tokens = set(tokens)
        for tok in unique_tokens:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    
    # Sort by document frequency (descending) and take top max_features
    vocab = sorted(doc_freq.keys(), key=lambda x: doc_freq[x], reverse=True)[:max_features]
    vocab_index = {tok: i for i, tok in enumerate(vocab)}
    
    N = len(texts)
    tfidf_matrix = np.zeros((N, len(vocab)), dtype=np.float32)
    
    for doc_idx, tokens in enumerate(all_tokens):
        # Term frequency
        tf: dict[str, int] = {}
        for tok in tokens:
            if tok in vocab_index:
                tf[tok] = tf.get(tok, 0) + 1
        
        # Normalize TF (sublinear)
        for tok, count in tf.items():
            tfidf = (1 + math.log(count)) * math.log(N / (doc_freq[tok] + 1))
            tfidf_matrix[doc_idx, vocab_index[tok]] = tfidf
        
        # L2 normalize
        row_norm = np.linalg.norm(tfidf_matrix[doc_idx])
        if row_norm > 0:
            tfidf_matrix[doc_idx] /= row_norm
    
    return tfidf_matrix, vocab


def _compute_tfidf_cosine_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity using TF-IDF vectors."""
    try:
        # Preprocess for TF-IDF
        processed1 = preprocess_for_tfidf(text1)
        processed2 = preprocess_for_tfidf(text2)
        
        if not processed1.strip() or not processed2.strip():
            return 0.0
        
        tfidf_matrix, _ = _tfidf_vectorize([processed1, processed2])
        
        if SKLEARN_AVAILABLE:
            sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
            return float(sim_matrix[0, 0])
        else:
            # Manual cosine similarity
            vec1 = tfidf_matrix[0]
            vec2 = tfidf_matrix[1]
            dot = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot / (norm1 * norm2))
    except Exception:
        return 0.0


def _sentence_level_tfidf_matching(orig_sents: list[str], sub_sents: list[str]) -> tuple[list[MatchPassage], float]:
    """
    Perform sentence-level matching using TF-IDF + Cosine Similarity.
    Returns (matches, average_best_score).
    """
    if not orig_sents or not sub_sents:
        return [], 0.0
    
    # Preprocess all sentences for TF-IDF
    orig_processed = [preprocess_for_tfidf(s) for s in orig_sents]
    sub_processed = [preprocess_for_tfidf(s) for s in sub_sents]
    
    # Filter empty
    orig_valid = [(s, p) for s, p in zip(orig_sents, orig_processed) if p.strip()]
    sub_valid = [(s, p) for s, p in zip(sub_sents, sub_processed) if p.strip()]
    
    if not orig_valid or not sub_valid:
        return [], 0.0
    
    orig_sents_filtered, orig_proc_filtered = zip(*orig_valid)
    sub_sents_filtered, sub_proc_filtered = zip(*sub_valid)
    
    # Vectorize all sentences together
    all_texts = list(orig_proc_filtered) + list(sub_proc_filtered)
    tfidf_matrix, _ = _tfidf_vectorize(all_texts, max_features=5000)
    
    orig_vectors = tfidf_matrix[:len(orig_proc_filtered)]
    sub_vectors = tfidf_matrix[len(orig_proc_filtered):]
    
    matches = []
    best_scores = []
    
    for i, (sub_sent, sub_vec) in enumerate(zip(sub_sents_filtered, sub_vectors)):
        if len(sub_sent.split()) < 5:  # Skip very short sentences
            continue
        
        best_sim = 0.0
        best_orig = ""
        
        for j, (orig_sent, orig_vec) in enumerate(zip(orig_sents_filtered, orig_vectors)):
            if len(orig_sent.split()) < 5:
                continue
            
            # Cosine similarity
            sim = _cosine_sim(
                {k: v for k, v in enumerate(sub_vec) if v > 0},
                {k: v for k, v in enumerate(orig_vec) if v > 0}
            ) if SKLEARN_AVAILABLE else float(np.dot(sub_vec, orig_vec) / (np.linalg.norm(sub_vec) * np.linalg.norm(orig_vec) + 1e-10))
            
            if sim > best_sim:
                best_sim = sim
                best_orig = orig_sent
        
        if best_sim >= 0.3:  # Threshold for considering a match
            best_scores.append(best_sim)
            if best_sim >= 0.85:
                match_type = "exact"
            elif best_sim >= 0.65:
                match_type = "high"
            elif best_sim >= 0.45:
                match_type = "moderate"
            else:
                match_type = "paraphrased"
            
            matches.append(MatchPassage(
                submitted=sub_sent[:500],
                original=best_orig[:500],
                similarity=round(best_sim, 4),
                match_type=match_type,
                match_algorithm="tfidf_cosine"
            ))
    
    avg_score = sum(best_scores) / len(best_scores) if best_scores else 0.0
    return matches, avg_score


def _jaccard_based_matching(orig_text: str, sub_text: str) -> tuple[list[MatchPassage], dict]:
    """
    Compute Jaccard-based similarities at multiple levels.
    Returns (matches, metrics_dict).
    """
    orig_tokens = preprocess_for_matching(orig_text)
    sub_tokens = preprocess_for_matching(sub_text)
    
    # Token-level Jaccard
    token_sim = _jaccard(set(orig_tokens), set(sub_tokens))
    
    # Shingle (3-gram) Jaccard
    orig_shingles = word_shingles(orig_tokens, 3)
    sub_shingles = word_shingles(sub_tokens, 3)
    shingle_sim = _jaccard(orig_shingles, sub_shingles)
    
    # Character 5-gram Jaccard (good for catching partial word matches)
    orig_char_grams = char_ngrams(orig_text, 5)
    sub_char_grams = char_ngrams(sub_text, 5)
    char_gram_sim = _jaccard(orig_char_grams, sub_char_grams)
    
    # Sentence-level Jaccard matching
    orig_sents = sentence_tokenize(orig_text)
    sub_sents = sentence_tokenize(sub_text)
    
    matches = []
    sent_scores = []
    
    for s in sub_sents:
        s_tokens = set(preprocess_for_matching(s))
        if len(s_tokens) < 4:
            continue
        
        best = 0.0
        best_o = ""
        for o in orig_sents:
            o_tokens = set(preprocess_for_matching(o))
            if len(o_tokens) < 4:
                continue
            sc = _jaccard(s_tokens, o_tokens)
            if sc > best:
                best = sc
                best_o = o
        
        if best >= 0.4:
            sent_scores.append(best)
            if best >= 0.85:
                match_type = "exact"
            elif best >= 0.6:
                match_type = "high"
            else:
                match_type = "moderate"
            matches.append(MatchPassage(
                submitted=s[:500],
                original=best_o[:500],
                similarity=round(best, 4),
                match_type=match_type,
                match_algorithm="jaccard"
            ))
        elif best >= 0.25:
            sent_scores.append(best)
    
    sent_avg = sum(sent_scores) / len(sent_scores) if sent_scores else 0.0
    
    metrics = {
        "token_jaccard": token_sim,
        "shingle_jaccard": shingle_sim,
        "char_gram_jaccard": char_gram_sim,
        "sentence_jaccard_avg": sent_avg,
    }
    
    return matches, metrics


def _combine_matches(tfidf_matches: list[MatchPassage], jaccard_matches: list[MatchPassage]) -> list[MatchPassage]:
    """Combine and deduplicate matches from different algorithms."""
    # Create a key for deduplication (first 50 chars of submitted + original)
    def match_key(m: MatchPassage) -> str:
        return f"{m.submitted[:50]}||{m.original[:50]}"
    
    combined = {}
    
    # Prefer TF-IDF matches (more semantically accurate)
    for m in tfidf_matches:
        key = match_key(m)
        combined[key] = m
    
    # Add Jaccard matches that don't overlap significantly
    for m in jaccard_matches:
        key = match_key(m)
        if key not in combined:
            combined[key] = m
        else:
            # Keep the one with higher similarity
            if m.similarity > combined[key].similarity:
                combined[key] = m
    
    # Sort by similarity descending
    result = list(combined.values())
    result.sort(key=lambda m: m.similarity, reverse=True)
    
    return result[:50]  # Cap at top 50 matches


def compare_documents(original_text: str, submitted_text: str) -> dict[str, Any]:
    """
    Compare submitted text against original using multiple algorithms.
    
    Primary: TF-IDF + Cosine Similarity (semantic/structural similarity)
    Secondary: Jaccard at token, shingle, char-gram, and sentence levels
    
    Returns comprehensive similarity metrics and matched passages.
    """
    orig = (original_text or "").strip()
    sub = (submitted_text or "").strip()
    
    if not orig or not sub:
        raise ValueError("Both original and submitted text are required")
    
    # ============ PRIMARY: TF-IDF + Cosine Similarity ============
    tfidf_cosine_sim = _compute_tfidf_cosine_similarity(orig, sub)
    
    # ============ SECONDARY: Jaccard-based Metrics ============
    jaccard_matches, jaccard_metrics = _jaccard_based_matching(orig, sub)
    
    # ============ SENTENCE-LEVEL TF-IDF MATCHING ============
    orig_sents = sentence_tokenize(orig)
    sub_sents = sentence_tokenize(sub)
    tfidf_sent_matches, tfidf_sent_avg = _sentence_level_tfidf_matching(orig_sents, sub_sents)
    
    # ============ COMBINE MATCHES ============
    all_matches = _combine_matches(tfidf_sent_matches, jaccard_matches)
    
    # ============ COMPUTE FINAL WEIGHTED SCORE ============
    # Weights based on algorithm reliability for plagiarism detection
    weights = {
        "tfidf_cosine": 0.40,      # Primary: semantic + structural
        "token_jaccard": 0.15,     # Word overlap
        "shingle_jaccard": 0.15,   # Phrase overlap (3-grams)
        "char_gram_jaccard": 0.10, # Character-level (typos, partial words)
        "sentence_jaccard": 0.10,  # Sentence structure
        "sentence_tfidf": 0.10,    # Sentence-level semantic
    }
    
    overall = (
        tfidf_cosine_sim * weights["tfidf_cosine"] +
        jaccard_metrics["token_jaccard"] * weights["token_jaccard"] +
        jaccard_metrics["shingle_jaccard"] * weights["shingle_jaccard"] +
        jaccard_metrics["char_gram_jaccard"] * weights["char_gram_jaccard"] +
        jaccard_metrics["sentence_jaccard_avg"] * weights["sentence_jaccard"] +
        tfidf_sent_avg * weights["sentence_tfidf"]
    )
    
    overall_pct = round(min(max(overall * 100, 0), 100), 2)
    
    # ============ PREPARE RESPONSE ============
    match_dicts = [
        {
            "submitted": m.submitted,
            "original": m.original,
            "similarity": m.similarity,
            "match_type": m.match_type,
            "match_algorithm": m.match_algorithm,
        }
        for m in all_matches
    ]
    
    orig_word_count = len(tokenize_raw(orig))
    sub_word_count = len(tokenize_raw(sub))
    
    return {
        "similarity_percent": overall_pct,
        "tfidf_cosine_similarity": round(tfidf_cosine_sim * 100, 2),
        "token_overlap": round(jaccard_metrics["token_jaccard"] * 100, 2),
        "shingle_overlap": round(jaccard_metrics["shingle_jaccard"] * 100, 2),
        "char_gram_overlap": round(jaccard_metrics["char_gram_jaccard"] * 100, 2),
        "sentence_match_avg": round(jaccard_metrics["sentence_jaccard_avg"] * 100, 2),
        "sentence_tfidf_avg": round(tfidf_sent_avg * 100, 2),
        "matched_passage_count": len(match_dicts),
        "matched_passages": match_dicts,
        "submitted_word_count": sub_word_count,
        "original_word_count": orig_word_count,
        "submitted_sentence_count": len(sub_sents),
        "original_sentence_count": len(orig_sents),
        "scoring_method": (
            "Weighted ensemble: TF-IDF Cosine Similarity (40%), Token Jaccard (15%), "
            "3-gram Shingle Jaccard (15%), Character 5-gram Jaccard (10%), "
            "Sentence-level Jaccard (10%), Sentence-level TF-IDF Cosine (10%). "
            "Uses NLTK for tokenization, lemmatization, and stopword removal. "
            "Measures similarity to registered original document only — not internet-wide plagiarism."
        ),
        "disclaimer": (
            "A high similarity percentage indicates textual overlap with the registered "
            "original reference. It is not proof of intentional plagiarism and does not "
            "search external sources. Results should be reviewed by a human."
        ),
        "algorithm_details": {
            "primary": "TF-IDF + Cosine Similarity (sklearn)" if SKLEARN_AVAILABLE else "TF-IDF + Cosine Similarity (manual)",
            "secondary": "Jaccard (token, shingle, char-gram, sentence)",
            "nlp_preprocessing": "NLTK" if NLTK_AVAILABLE else "Regex fallback",
            "lemmatization": "WordNet" if NLTK_AVAILABLE else "Disabled",
            "stopword_removal": "NLTK English" if NLTK_AVAILABLE else "Built-in list",
        }
    }


# Backward compatibility
def compare_documents_legacy(original_text: str, submitted_text: str) -> dict[str, Any]:
    """Legacy interface matching the old API."""
    result = compare_documents(original_text, submitted_text)
    return {
        "similarity_percent": result["similarity_percent"],
        "token_overlap": result["token_overlap"],
        "shingle_overlap": result["shingle_overlap"],
        "sentence_match_avg": result["sentence_match_avg"],
        "matched_passage_count": result["matched_passage_count"],
        "matched_passages": result["matched_passages"],
        "submitted_word_count": result["submitted_word_count"],
        "original_word_count": result["original_word_count"],
        "scoring_method": result["scoring_method"],
        "disclaimer": result["disclaimer"],
    }