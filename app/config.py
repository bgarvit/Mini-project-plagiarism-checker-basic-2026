"""Application configuration — loads from environment and optional .env file."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOCUMENTS_DIR = BASE_DIR / "documents"
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = DATA_DIR / "tmp"


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv()

SECRET_KEY = os.getenv("PLAGIFY_SECRET_KEY", "plagify-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))

# File limits
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".doc"}
MIN_TEXT_CHARS = 50
MAX_TEXT_CHARS = 500_000

# Google OAuth (optional)
_raw_google = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_ID = "" if (not _raw_google or _raw_google.startswith("YOUR_")) else _raw_google

# Supabase — leave empty for local SQLite fallback for original documents
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "original-documents").strip()
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

# AI detection providers (optional paid APIs; offline lmscan preferred when installed)
GPTZERO_API_KEY = os.getenv("GPTZERO_API_KEY", "").strip()
SAPLING_API_KEY = os.getenv("SAPLING_API_KEY", "").strip()
# Prefer: lmscan (local) → GPTZero API → Sapling API → built-in heuristic
AI_DETECTION_PROVIDER = os.getenv("AI_DETECTION_PROVIDER", "auto").strip().lower()

# CORS
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")
    if o.strip()
]
