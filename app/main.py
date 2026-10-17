"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, DATA_DIR, FRONTEND_DIR, TEMP_DIR
from app.database import original_store
from app.database.sqlite_users import init_user_db
from app.routes import ai_detection, auth, plagiarism

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Plagify API",
    version="2.0.0",
    description="AI detection and original-document plagiarism checker",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ai_detection.router)
app.include_router(plagiarism.router)


@app.on_event("startup")
def on_startup() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    init_user_db()
    original_store.init_original_table()


@app.get("/api/health")
def health() -> dict:
    from app.config import AI_DETECTION_PROVIDER, SUPABASE_ENABLED

    return {
        "status": "ok",
        "service": "plagify-backend",
        "version": "2.0.0",
        "supabase_enabled": SUPABASE_ENABLED,
        "ai_detection_provider": AI_DETECTION_PROVIDER,
    }


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
