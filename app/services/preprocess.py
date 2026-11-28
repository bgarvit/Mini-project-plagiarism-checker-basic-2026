"""Enhanced text preprocessing utilities using NLTK for plagiarism detection."""

import re
import string
from typing import Iterable, Optional
from functools import lru_cache

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.stem import SnowballStemmer, WordNetLemmatizer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Download required NLTK data on first import
if NLTK_AVAILABLE:
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', quiet=True)
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet', quiet=True)
    try:
        nltk.data.find('corpora/omw-1.4')
    except LookupError:
        nltk.download('omw-1.4', quiet=True)


# Fallback regex tokenizer (when NLTK unavailable)
WORD_RE = re.compile(r"[a-z0-9]+")
SENT_RE = re.compile(r"(?<=[.!?])\s+")

# English stopwords (fallback if NLTK unavailable)
FALLBACK_STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
    'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
    'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
    'have', 'had', 'what', 'when', 'where', 'who', 'which', 'why', 'how',
    'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'can', 'just', 'should', 'now', 'i', 'me', 'my', 'myself', 'we',
    'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
    'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
    'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs',
    'themselves', 'what', 'which', 'who', 'whom', 'am', 'is', 'are',
    'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
    'do', 'does', 'did', 'doing', 'would', 'could', 'should', 'may',
    'might', 'must', 'shall', 'will'
}

# Initialize stemmer and lemmatizer
_stemmer: Optional[SnowballStemmer] = None
_lemmatizer: Optional[WordNetLemmatizer] = None
_stopwords_set: Optional[set] = None


def _get_stemmer() -> SnowballStemmer:
    global _stemmer
    if _stemmer is None:
        _stemmer = SnowballStemmer('english')
    return _stemmer


def _get_lemmatizer() -> WordNetLemmatizer:
    global _lemmatizer
    if _lemmatizer is None:
        _lemmatizer = WordNetLemmatizer()
    return _lemmatizer


def _get_stopwords() -> set:
    global _stopwords_set
    if _stopwords_set is None:
        if NLTK_AVAILABLE:
            try:
                _stopwords_set = set(stopwords.words('english'))
            except:
                _stopwords_set = FALLBACK_STOPWORDS
        else:
            _stopwords_set = FALLBACK_STOPWORDS
    return _stopwords_set


def normalize(text: str) -> str:
    """Lowercase text and collapse whitespace."""
    if not text:
        return ""
    return " ".join(text.lower().split())


def tokenize(text: str, remove_stopwords: bool = True, use_stemming: bool = False, use_lemmatization: bool = True) -> list[str]:
    """
    Tokenize text into words with optional stopword removal and stemming/lemmatization.
    
    Args:
        text: Input text
        remove_stopwords: Whether to remove stopwords
        use_stemming: Apply stemming (Snowball)
        use_lemmatization: Apply lemmatization (WordNet) - preferred over stemming
    
    Returns:
        List of processed tokens
    """
    if not text:
        return []
    
    normalized = normalize(text)
    
    if NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(normalized)
        except:
            tokens = WORD_RE.findall(normalized)
    else:
        tokens = WORD_RE.findall(normalized)
    
    # Filter alphanumeric tokens only
    tokens = [t for t in tokens if re.match(r'^[a-z0-9]+$', t)]
    
    if remove_stopwords:
        stop_words = _get_stopwords()
        tokens = [t for t in tokens if t not in stop_words]
    
    if use_lemmatization:
        lemmatizer = _get_lemmatizer()
        tokens = [lemmatizer.lemmatize(t) for t in tokens]
    elif use_stemming:
        stemmer = _get_stemmer()
        tokens = [stemmer.stem(t) for t in tokens]
    
    return tokens


def tokenize_raw(text: str) -> list[str]:
    """Simple tokenization without stopword removal - for TF-IDF vectorization."""
    if not text:
        return []
    normalized = normalize(text)
    if NLTK_AVAILABLE:
        try:
            tokens = word_tokenize(normalized)
        except:
            tokens = WORD_RE.findall(normalized)
    else:
        tokens = WORD_RE.findall(normalized)
    return [t for t in tokens if re.match(r'^[a-z0-9]+$', t)]


def sentence_tokenize(text: str) -> list[str]:
    """Split text into sentences using NLTK or regex fallback."""
    if not text:
        return []
    if NLTK_AVAILABLE:
        try:
            sentences = sent_tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except:
            pass
    # Fallback regex
    parts = [s.strip() for s in SENT_RE.split(text) if s.strip()]
    out = []
    for p in parts:
        if len(p) > 400:
            chunks = re.split(r"\n+", p)
            out.extend(c.strip() for c in chunks if c.strip())
        else:
            out.append(p)
    return out


def word_shingles(tokens: list[str], size: int = 3) -> set[str]:
    """Build fixed-size word n-gram shingles from a token list."""
    if not tokens or len(tokens) < size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def char_ngrams(text: str, size: int = 5) -> set[str]:
    """Build character n-grams from normalized text (ignoring spaces)."""
    compact = normalize(text).replace(" ", "")
    if not compact or len(compact) < size:
        return {compact} if compact else set()
    return {compact[i:i + size] for i in range(len(compact) - size + 1)}


def term_frequency(tokens: Iterable[str]) -> dict[str, int]:
    """Count how often each token appears."""
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def preprocess_for_tfidf(text: str) -> str:
    """
    Preprocess text for TF-IDF vectorization.
    Returns space-joined tokens (stopwords kept for vectorizer's built-in handling).
    """
    tokens = tokenize_raw(text)
    return " ".join(tokens)


def preprocess_for_matching(text: str) -> list[str]:
    """
    Preprocess text for similarity matching (Jaccard, etc.).
    Returns tokens with stopwords removed and lemmatized.
    """
    return tokenize(text, remove_stopwords=True, use_lemmatization=True)


# Backward compatibility
def get_tokens(text: str) -> list[str]:
    """Legacy alias for tokenize()."""
    return tokenize(text)