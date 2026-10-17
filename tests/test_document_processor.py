import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.document_processor import content_hash, normalize_text, validate_upload


def test_normalize_collapses_whitespace():
    assert "a b" in normalize_text("a   \t  b\n\n\nc")


def test_hash_stable():
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_validate_rejects_bad_ext():
    try:
        validate_upload("x.exe", b"MZ")
        assert False
    except ValueError:
        pass


def test_validate_txt_ok():
    name = validate_upload("note.txt", b"hello world " * 20)
    assert name.endswith(".txt")
