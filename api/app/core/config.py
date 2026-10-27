"""Centralized, typed settings for the FastAPI service.

Values are read from the process environment / a `.env` file at the `api/`
root via `pydantic-settings`. See `.env.example` for the documented list,
and this project's README "Environment variables" section for which values
must match the sibling `backend/` project's own `.env` byte-for-byte
(`SHARED_JWT_SECRET`, `APP_FRONTEND_URL`).
"""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(API_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Django ORM integration ---------------------------------------
    BACKEND_DIR: Path = (API_ROOT.parent / "backend").resolve()
    DJANGO_SETTINGS_MODULE: str = "config.settings.local"

    # --- Django <-> FastAPI bridge (SHARED with backend/.env) ----------
    SHARED_JWT_SECRET: str = "change-me-shared-jwt-secret-min-32-bytes-of-entropy"
    APP_FRONTEND_URL: str = "http://localhost:5173"

    # --- This service's own token TTLs ---------------------------------
    ACCESS_TOKEN_TTL_SECONDS: int = 900
    REFRESH_TOKEN_TTL_SECONDS: int = 1_209_600

    # --- Redis (SHARED with backend/.env) -------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- CORS -------------------------------------------------------------
    # Comma-separated string on purpose (not `list[str]`): pydantic-settings
    # tries to JSON-decode any complex-typed env var *before* field
    # validators ever run, which rejects a plain CSV value like
    # `http://a,http://b`. Keeping this a `str` and exposing `CORS_ORIGINS`
    # as a computed list property sidesteps that entirely.
    CORS_ORIGINS_RAW: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )

    # --- Environment switch ("local" | "production") -----------------------
    ENV: str = "local"

    @property
    def CORS_ORIGINS(self) -> list[str]:  # noqa: N802 (matches other SCREAMING_CASE settings)
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()
