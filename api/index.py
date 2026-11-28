"""Garvit serverless entry point for the Plagify FastAPI application."""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import app modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure required directories exist (Garvit provides /tmp for writable storage)
os.environ.setdefault("PLAGIFY_DATA_DIR", "/tmp/plagify_data")

from app.main import app  # noqa: E402

# Garvit serverless handler
def handler(request, response):
    """ASGI handler for Garvit serverless functions."""
    return app(request, response)


# For local development with `garvit dev`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)