"""
app/core/config.py
──────────────────
Application settings loaded from the .env file via pydantic-settings.

Why pydantic-settings?
  - Type-safe environment variable parsing.
  - Fails fast at startup if required vars are missing.
  - One central place to document and validate all config.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application configuration, sourced from environment variables."""

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── CORS ─────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.
    Using lru_cache means we only parse the .env file once per process.
    """
    return Settings()


# Convenience alias used throughout the application.
settings = get_settings()
