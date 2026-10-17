"""String-matching similarity algorithms."""



import math

import re

from typing import Iterable



from .preprocess import char_ngrams, term_frequency, tokenize, word_shingles



SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")





def jaccard_similarity(a: set[str], b: set[str]) -> float:

    """Jaccard index: |A intersect B| / |A union B|."""

    if not a or not b:

        return 0.0

    intersection = a & b

    union = a | b

    return len(intersection) / len(union)





def longest_common_substring_length(a: str, b: str) -> int:

    """Dynamic-programming longest common substring length."""

    if not a or not b:

        return 0



    previous = [0] * (len(b) + 1)

    best = 0



    for i in range(1, len(a) + 1):

        current = [0] * (len(b) + 1)

        for j in range(1, len(b) + 1):

            if a[i - 1] == b[j - 1]:

                current[j] = previous[j - 1] + 1

                best = max(best, current[j])

        previous = current



    return best





def lcs_ratio(text_a: str, text_b: str) -> float:

    """Longest common substring length divided by the shorter text length."""

    compact_a = text_a.replace(" ", "")

    compact_b = text_b.replace(" ", "")

    if not compact_a or not compact_b:

        return 0.0

    lcs_len = longest_common_substring_length(compact_a, compact_b)

    return lcs_len / min(len(compact_a), len(compact_b))





def cosine_similarity(vec_a: dict[str, int], vec_b: dict[str, int]) -> float:

    """Cosine similarity between two term-frequency vectors."""

    if not vec_a or not vec_b:

        return 0.0



    shared = set(vec_a) & set(vec_b)

    dot = sum(vec_a[token] * vec_b[token] for token in shared)

    mag_a = math.sqrt(sum(value * value for value in vec_a.values()))

    mag_b = math.sqrt(sum(value * value for value in vec_b.values()))



    if mag_a == 0 or mag_b == 0:

        return 0.0

    return dot / (mag_a * mag_b)





def overlap_coefficient(a: set[str], b: set[str]) -> float:

    """Overlap coefficient: |A intersect B| / min(|A|, |B|)."""

    if not a or not b:

        return 0.0

    return len(a & b) / min(len(a), len(b))





class SimilarityReport:

    """Similarity scores produced by multiple matching techniques."""



    __slots__ = (

        "jaccard_words",

        "jaccard_shingles",

        "char_ngram",

        "cosine",

        "lcs",

        "overlap",

        "overall",

    )



    def __init__(

        self,

        jaccard_words: float,

        jaccard_shingles: float,

        char_ngram: float,

        cosine: float,

        lcs: float,

        overlap: float,

        overall: float,

    ) -> None:

        self.jaccard_words = jaccard_words

        self.jaccard_shingles = jaccard_shingles

        self.char_ngram = char_ngram

        self.cosine = cosine

        self.lcs = lcs

        self.overlap = overlap

        self.overall = overall



    def as_dict(self) -> dict[str, float]:

        return {

            "jaccard_words": self.jaccard_words,

            "jaccard_shingles": self.jaccard_shingles,

            "char_ngram": self.char_ngram,

            "cosine": self.cosine,

            "lcs": self.lcs,

            "overlap": self.overlap,

            "overall": self.overall,

        }





def compare_texts(

    query: str,

    reference: str,

    shingle_size: int = 3,

    char_ngram_size: int = 4,

) -> SimilarityReport:

    """Compare two texts using several string-matching techniques."""

    query_tokens = tokenize(query)

    reference_tokens = tokenize(reference)



    word_set_a = set(query_tokens)

    word_set_b = set(reference_tokens)

    shingle_a = word_shingles(query_tokens, shingle_size)

    shingle_b = word_shingles(reference_tokens, shingle_size)

    char_a = char_ngrams(query, char_ngram_size)

    char_b = char_ngrams(reference, char_ngram_size)



    scores = {

        "jaccard_words": jaccard_similarity(word_set_a, word_set_b),

        "jaccard_shingles": jaccard_similarity(shingle_a, shingle_b),

        "char_ngram": jaccard_similarity(char_a, char_b),

        "cosine": cosine_similarity(

            term_frequency(query_tokens),

            term_frequency(reference_tokens),

        ),

        "lcs": lcs_ratio(query, reference),

        "overlap": overlap_coefficient(word_set_a, word_set_b),

    }



    weights = {

        "jaccard_words": 0.15,

        "jaccard_shingles": 0.25,

        "char_ngram": 0.15,

        "cosine": 0.25,

        "lcs": 0.10,

        "overlap": 0.10,

    }

    overall = sum(scores[key] * weights[key] for key in scores)

    return SimilarityReport(overall=overall, **scores)





def split_segments(text: str) -> list[str]:

    """Split text into paragraph and sentence segments for localized matching."""

    segments: list[str] = []

    for paragraph in text.split("\n\n"):

        paragraph = paragraph.strip()

        if not paragraph:

            continue

        segments.append(paragraph)

        for sentence in SENTENCE_SPLIT_RE.split(paragraph):

            sentence = sentence.strip()

            if sentence and sentence not in segments:

                segments.append(sentence)

    return segments





def compare_with_document(

    query: str,

    reference: str,

    shingle_size: int = 3,

    char_ngram_size: int = 4,

) -> SimilarityReport:

    """Compare input by matching each query segment to the closest reference segment."""

    reference_segments = split_segments(reference)

    if not reference_segments:

        return compare_texts(query, reference, shingle_size, char_ngram_size)



    query_segments = split_segments(query) or [query]

    best_reports: list[SimilarityReport] = []



    for query_segment in query_segments:

        segment_scores = [

            compare_texts(query_segment, reference_segment, shingle_size, char_ngram_size)

            for reference_segment in reference_segments

        ]

        best_reports.append(max(segment_scores, key=lambda report: report.overall))



    if len(best_reports) == 1:

        return best_reports[0]



    keys = [

        "jaccard_words",

        "jaccard_shingles",

        "char_ngram",

        "cosine",

        "lcs",

        "overlap",

    ]

    averaged = {

        key: sum(getattr(report, key) for report in best_reports) / len(best_reports)

        for key in keys

    }

    weights = {

        "jaccard_words": 0.15,

        "jaccard_shingles": 0.25,

        "char_ngram": 0.15,

        "cosine": 0.25,

        "lcs": 0.10,

        "overlap": 0.10,

    }

    overall = sum(averaged[key] * weights[key] for key in keys)

    return SimilarityReport(overall=overall, **averaged)





def find_matching_phrases(

    query: str,

    reference: str,

    min_length: int = 20,

) -> list[str]:

    """Return shared substrings above a minimum character length."""

    compact_query = " ".join(query.lower().split())

    compact_reference = " ".join(reference.lower().split())

    matches: list[str] = []



    for start in range(len(compact_query)):

        for end in range(start + min_length, len(compact_query) + 1):

            fragment = compact_query[start:end]

            if fragment in compact_reference and fragment not in matches:

                if not any(fragment in existing for existing in matches):

                    matches = [m for m in matches if m not in fragment]

                    matches.append(fragment)



    return sorted(matches, key=len, reverse=True)

