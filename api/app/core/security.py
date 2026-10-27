"""JWT minting/verification for this service's own access/refresh tokens,
plus verification of the bridge JWT minted by the Django backend
(`apps.users.services.issue_bridge_token`).

All three token kinds (`bridge`, `access`, `refresh`) are HS256, signed with
the same `SHARED_JWT_SECRET` the Django backend uses for the bridge token.
Using one shared secret for our own access/refresh tokens too (rather than a
second FastAPI-only secret) is a deliberate simplification: there is only
ever one signing key to rotate, and nothing here is shared cross-service
except the bridge token, so there's no actual security benefit to a second
secret — just more env vars to keep in sync.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt

from app.core.config import settings

TokenType = Literal["access", "refresh", "bridge"]


class InvalidTokenError(Exception):
    """Raised for any bad/expired/wrong-type token. Callers map this to 401."""


def _encode(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.SHARED_JWT_SECRET, algorithm="HS256")


def create_access_token(user: Any) -> str:
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": str(user.pk),
        "email": user.email,
        "role": user.role,
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS),
    }
    return _encode(claims)


def create_refresh_token(user: Any) -> str:
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": str(user.pk),
        "typ": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS),
    }
    return _encode(claims)


def decode_token(token: str, expected_typ: TokenType) -> dict[str, Any]:
    """Decodes and validates signature + expiry + `typ` claim.

    Raises `InvalidTokenError` on bad signature, expiry, malformed token, or
    a `typ` claim that doesn't match `expected_typ`. Never raises a raw PyJWT
    exception so callers (FastAPI dependencies, routes) have one exception
    type to catch and turn into a generic 401 — never leaking which specific
    validation failed.
    """
    try:
        claims = jwt.decode(token, settings.SHARED_JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if claims.get("typ") != expected_typ:
        raise InvalidTokenError(f"expected typ={expected_typ!r}, got {claims.get('typ')!r}")

    return claims


def verify_bridge_token(token: str) -> dict[str, Any]:
    """Verifies a bridge JWT minted by `apps.users.services.issue_bridge_token`.

    Only checks signature + expiry + `typ == "bridge"` here. The production
    replay check (consuming the `jti` against Redis) is a separate step —
    see `app/core/redis_client.py::consume_bridge_jti` — performed by the
    `/auth/exchange` route after this succeeds.
    """
    return decode_token(token, expected_typ="bridge")
