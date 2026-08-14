"""
app/main.py
───────────
FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance with metadata.
  - Configure CORS for the React frontend.
  - Mount all API routers under /api.
  - Expose health check endpoint.

Why configure CORS here?
  - CORS headers must be set at the framework level before any route handler
    runs. FastAPI's CORSMiddleware handles the browser's preflight OPTIONS
    requests automatically.
  - FRONTEND_URL comes from config so local dev and production differ only
    via environment variables, never by code changes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, games, users
from app.core.config import settings

app = FastAPI(
    title="ClickRush API",
    description="Backend API for the ClickRush 60-second click challenge.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(games.router, prefix="/api")


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"], summary="Health check")
def health() -> dict:
    """Returns 200 OK when the server is running."""
    return {"status": "ok"}
