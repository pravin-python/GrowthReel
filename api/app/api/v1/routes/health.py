"""Health checks. VAPT fix #16: `GET /health` is public and reveals nothing;
`GET /health/detailed` requires auth and only ever returns booleans/strings —
never a hostname, internal IP, file path, or stack trace.
"""
from __future__ import annotations

import importlib.metadata

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import HealthDetailedOut, HealthOut
from app.core.redis_client import check_connection

router = APIRouter()


def _app_version() -> str:
    try:
        return importlib.metadata.version("growthreel-api")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


def _database_reachable() -> bool:
    from django.db import connections

    try:
        connections["default"].cursor().close()
        return True
    except Exception:
        return False


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut()


@router.get("/health/detailed", response_model=HealthDetailedOut)
async def health_detailed(user=Depends(get_current_user)) -> HealthDetailedOut:
    db_ok = await sync_to_async(_database_reachable)()
    cache_ok = await check_connection()
    return HealthDetailedOut(
        database="ok" if db_ok else "unavailable",
        cache="ok" if cache_ok else "unavailable",
        version=_app_version(),
    )
