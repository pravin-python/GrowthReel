"""Thin Redis wrapper. Only two routes in this whole service ever touch
Redis: `/auth/exchange` (bridge-token replay check) and `/auth/refresh` /
`/auth/logout` (refresh-token revocation). Every other route never imports
this module, so a Redis outage cannot affect them.
"""
from __future__ import annotations

import logging

import redis.asyncio as redis_asyncio

from app.core.config import settings

logger = logging.getLogger("app")

BRIDGE_JTI_PREFIX = "bridge-jti:"
REVOKED_REFRESH_PREFIX = "revoked-refresh:"

_client: redis_asyncio.Redis | None = None


def get_redis() -> redis_asyncio.Redis:
    """Returns a lazily-created, process-wide `redis.asyncio` client.

    Creating the client does not itself open a connection (redis-py connects
    lazily on first command), so this never raises even if Redis is down.
    """
    global _client
    if _client is None:
        _client = redis_asyncio.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def consume_bridge_jti(jti: str) -> bool:
    """Atomic get-and-delete replay check for a bridge token's `jti`.

    - In production: the Django backend records `bridge-jti:<jti>` in its
      Redis-backed cache the instant it mints the token (see
      `backend/apps/users/services.py::issue_bridge_token`). This does an
      atomic `GETDEL` against the *same* Redis instance — if the key is
      missing, the token was never seen (shouldn't happen) or has already
      been consumed/expired, so we reject it. This is the authoritative
      single-use enforcement for the bridge token.

    - In local/dev (`ENV != "production"`): this check is skipped entirely
      and we rely solely on the JWT's own 60-second `exp`. Reason: local
      Django (`config.settings.local`) uses `LocMemCache`, which lives
      entirely inside the Django process's own memory — a separate FastAPI
      process can never see the `jti` that Django recorded, Redis or not.
      Pointing both services at a real local Redis would fix this, but
      backend/README.md's reviewer notes explicitly call this out as
      intentional and acceptable for local dev with a single consumer (see
      "Local cache backend is not Redis"). Attempting the Redis check in
      local dev anyway would always-reject (no key was ever written there
      by this separate process) for no real security benefit in a
      single-developer, single-process local setup.

    - Redis connection errors (any environment): caught and logged rather
      than raised. In production, this fails *open* (returns True) rather
      than hard-rejecting every login during a Redis outage — the bridge
      JWT's signature + 60s expiry are still fully enforced regardless, so
      losing the replay check only means a captured bridge token could be
      replayed within that 60s window during the outage, an acceptable,
      documented degradation versus taking down login entirely.
    """
    if not settings.is_production:
        return True

    key = f"{BRIDGE_JTI_PREFIX}{jti}"
    try:
        client = get_redis()
        # GETDEL is atomic: a concurrent replay can never both succeed.
        value = await client.getdel(key)
        return value is not None
    except Exception:
        logger.exception("redis.consume_bridge_jti failed; failing open for jti=%s", jti)
        return True


async def revoke_refresh_jti(jti: str, ttl_seconds: int) -> None:
    """Best-effort revoke of a refresh token's `jti`, used by `/auth/logout`.

    Never raises — a Redis outage must not stop logout from clearing the
    cookie and returning 204.
    """
    if ttl_seconds <= 0:
        return
    try:
        client = get_redis()
        await client.set(f"{REVOKED_REFRESH_PREFIX}{jti}", "1", ex=ttl_seconds)
    except Exception:
        logger.exception("redis.revoke_refresh_jti failed for jti=%s", jti)


async def is_refresh_jti_revoked(jti: str) -> bool:
    """Checked by `/auth/refresh` before honoring a refresh token.

    Same local/dev vs. production split as `consume_bridge_jti`: in local
    dev this always returns False (no revocation list is consulted), and a
    Redis connection error fails *open* (treated as not-revoked) so an
    outage degrades gracefully instead of locking everyone out.
    """
    if not settings.is_production:
        return False

    try:
        client = get_redis()
        return bool(await client.exists(f"{REVOKED_REFRESH_PREFIX}{jti}"))
    except Exception:
        logger.exception("redis.is_refresh_jti_revoked failed; failing open for jti=%s", jti)
        return False


async def check_connection() -> bool:
    """Used by `GET /health/detailed`. Never raises."""
    try:
        client = get_redis()
        return bool(await client.ping())
    except Exception:
        return False
