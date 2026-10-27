"""Aggregates every v1 router under the `/api/v1` prefix."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth, health, leads, posts
from app.api.v1.ws import notifications

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(leads.router, tags=["leads"])
api_router.include_router(posts.router, tags=["posts"])
api_router.include_router(notifications.router, tags=["ws"])
