"""Business logic for the users app, including the Django <-> FastAPI bridge.

`issue_bridge_token` is the exact mechanism the FastAPI service depends on:
after a normal Django session login succeeds, the browser is redirected to
`APP_FRONTEND_URL/auth/callback?token=<bridge_jwt>`. The bridge JWT is a
short-lived (60s), single-use HS256 token signed with `SHARED_JWT_SECRET`
(the same secret the FastAPI service is configured with), so FastAPI can
verify it and mint its own access/refresh token pair without ever calling
back into Django.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache

from apps.users.models import User

BRIDGE_TOKEN_TYPE = "bridge"
BRIDGE_JTI_CACHE_PREFIX = "bridge-jti:"
# Cache timeout is intentionally a little longer than the token's own TTL so
# the jti is still recorded as "seen" for a few seconds after expiry.
BRIDGE_JTI_CACHE_TIMEOUT_SECONDS = 70


def issue_bridge_token(user: User) -> str:
    """Mints a short-lived, single-use bridge JWT for `user`.

    Claims: `sub` (user UUID as str), `email`, `role`, `jti` (uuid4, for
    single-use enforcement), `iat`, `exp` (60s from mint time), and
    `typ: "bridge"`.

    The `jti` is recorded in Django's cache framework as soon as it's
    minted (`bridge-jti:<jti>`), which is advisory, best-effort replay
    protection on this side only. The authoritative single-use check is the
    FastAPI service's own lookup against the same Redis in production; for
    local development, this Django-side cache write is the only enforcement
    in place, which is acceptable because local dev has a single consumer.
    """
    now = datetime.now(tz=timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user.pk),
        "email": user.email,
        "role": user.role,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(seconds=settings.BRIDGE_JWT_TTL_SECONDS),
        "typ": BRIDGE_TOKEN_TYPE,
    }
    token = jwt.encode(payload, settings.SHARED_JWT_SECRET, algorithm="HS256")

    cache.set(
        f"{BRIDGE_JTI_CACHE_PREFIX}{jti}",
        1,
        timeout=BRIDGE_JTI_CACHE_TIMEOUT_SECONDS,
    )

    return token


def verify_password(user: User, raw_password: str) -> bool:
    """Thin wrapper mirroring Django's own password check.

    The FastAPI service has full ORM access to this same database, so in
    practice it will just call
    `django.contrib.auth.hashers.check_password(raw_password, user.password)`
    directly rather than importing this function. This wrapper exists so
    Django-side code (and anything documenting the contract) has one
    obvious, importable place that mirrors exactly what the FastAPI side is
    expected to do.
    """
    return check_password(raw_password, user.password)
