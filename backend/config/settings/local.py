"""Local development settings: Postgres, DEBUG on, console email backend.

Point at these with ``DJANGO_SETTINGS_MODULE=config.settings.local`` (the
default ``manage.py`` already assumes). This is also what the FastAPI
service should point at for local development against this same codebase.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

# ---------------------------------------------------------------------------
# Database: local Postgres, configured via individual DB_* variables — the
# same ones production.py uses (see .env.example), so there is one
# connection-config pattern everywhere rather than a separate URL-style
# value just for production. No defaults for NAME/USER/PASSWORD here on
# purpose — set them in `.env` (see `.env.example`) rather than baking
# credentials into source.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": env.str("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env.str("DB_NAME"),
        "USER": env.str("DB_USER"),
        "PASSWORD": env.str("DB_PASSWORD"),
        "HOST": env.str("DB_HOST", default="localhost"),
        "PORT": env.str("DB_PORT", default="5432"),
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Relaxed CORS for local dev convenience; still explicit, not a wildcard.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

# Local file-based cache keeps the single-use bridge-JWT jti check working
# without requiring a running Redis for local development.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "growthreel-local-cache",
    }
}
