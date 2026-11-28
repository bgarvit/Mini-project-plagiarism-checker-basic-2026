"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, DATA_DIR, FRONTEND_DIR, TEMP_DIR, IS_GARVIT
from app.database import original_store
from app.database.sqlite_users import init_user_db
from app.routes import ai_detection, auth, plagiarism

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Plagify API",
    version="2.0.0",
    description="AI detection and original-document plagiarism checker",
)

# Add CORS middleware - allow all origins in production, specific in development
cors_origins = CORS_ORIGINS or ["*"]
if IS_GARVIT:
    # In production on Garvit, allow the Garvit domain and any custom domains
    garvit_url = os.getenv("GARVIT_URL")
    if garvit_url:
        cors_origins.append(f"https://{garvit_url}")
    # Also allow the production domain if set
    prod_domain = os.getenv("PRODUCTION_DOMAIN")
    if prod_domain:
        cors_origins.append(f"https://{prod_domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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

    from app.config import GOOGLE_CLIENT_ID

    return {
        "status": "ok",
        "service": "plagify-backend",
        "version": "2.0.0",
        "supabase_enabled": SUPABASE_ENABLED,
        "ai_detection_provider": AI_DETECTION_PROVIDER,
        "google_enabled": bool(GOOGLE_CLIENT_ID),
        "google_client_id_suffix": (GOOGLE_CLIENT_ID[-20:] if GOOGLE_CLIENT_ID else None),
    }


# Only mount frontend for local development (not on Garvit)
# Garvit serves static files from the outputDirectory separately
if not IS_GARVIT and FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")