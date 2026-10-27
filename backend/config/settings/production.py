"""Production settings: Postgres, Redis cache, security hardening on."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# ---------------------------------------------------------------------------
# Database: Postgres via the same discrete DB_* variables local.py uses (see
# .env.example) — one connection-config pattern everywhere, instead of a
# separate DATABASE_URL-style value just for production. The one thing
# production needs that local dev doesn't: a granular SSL mode, via
# `DB_SSLMODE` (defaults to "require" — a real managed Postgres is almost
# always reachable only over TLS; set to "disable" only for a same-host/
# same-network deployment that has no TLS listener at all).
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": env.str("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": env.str("DB_NAME"),
        "USER": env.str("DB_USER"),
        "PASSWORD": env.str("DB_PASSWORD"),
        "HOST": env.str("DB_HOST", default="localhost"),
        "PORT": env.str("DB_PORT", default="5432"),
        "OPTIONS": {"sslmode": env.str("DB_SSLMODE", default="require")},
        # Persistent DB connections. For real production traffic, pgbouncer
        # (or the django-db-connection-pool package) is the right answer for
        # connection pooling under load; CONN_MAX_AGE alone is a reasonable,
        # low-effort middle-ground for a single-process/gunicorn-worker
        # deployment.
        "CONN_MAX_AGE": 60,
    }
}

# ---------------------------------------------------------------------------
# Cache: Django 5.2's built-in Redis cache backend (no extra package needed).
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.str("REDIS_URL"),
    }
}

# ---------------------------------------------------------------------------
# Security hardening
#
# All of this assumes a real TLS-terminating proxy in front of the app (the
# normal case). `DJANGO_FORCE_HTTPS=false` is an escape hatch for running
# these *otherwise*-production settings (real Postgres/Redis) in a local
# docker-compose stack served over plain HTTP, so the compose environment can
# exercise the Postgres/Redis wiring without tripping an HTTPS redirect loop
# or silently dropping Secure cookies. Never set this false in a real
# deployment.
# ---------------------------------------------------------------------------
DJANGO_FORCE_HTTPS = env.bool("DJANGO_FORCE_HTTPS", default=True)

SESSION_COOKIE_SECURE = DJANGO_FORCE_HTTPS
CSRF_COOKIE_SECURE = DJANGO_FORCE_HTTPS
SECURE_SSL_REDIRECT = DJANGO_FORCE_HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000 if DJANGO_FORCE_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = DJANGO_FORCE_HTTPS
SECURE_HSTS_PRELOAD = DJANGO_FORCE_HTTPS

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ---------------------------------------------------------------------------
# Static files: gunicorn alone does not serve STATIC_ROOT, so production (and
# the docker-compose stack, which runs via gunicorn too) needs WhiteNoise to
# serve the collected, hashed, compressed static files (admin CSS/JS, the
# built Tailwind stylesheet) directly from the app process — no separate
# nginx static mount required. `requirements/production.txt` already depends
# on `whitenoise`; this is the settings half of actually wiring it in.
# ---------------------------------------------------------------------------
MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
