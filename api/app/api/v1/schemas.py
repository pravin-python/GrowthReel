"""Pydantic request/response models for `/api/v1`.

Field shapes here are the literal contract the React app (`frontend-app/`)
is built against — see its `src/lib/types.ts`, which mirrors this file by
hand on the other side. Notably: every `id` field (including `Lead.id` and
`Post.id`, whose underlying Django primary keys are plain auto-incrementing
integers, not UUIDs) is serialized as a `str` here, because that's what
`frontend-app/src/lib/types.ts` declares (`id: string`) — do not "fix" these
to `int` without updating that file too.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BridgeExchangeRequest(BaseModel):
    bridge_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: str


class LeadOut(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    company: str
    status: str
    source: str
    owner_id: str | None
    created_at: datetime


class LeadStatusUpdate(BaseModel):
    status: str


class PostOut(BaseModel):
    id: str
    title: str
    slug: str
    status: str
    published_at: datetime | None
    author_email: str


class HealthOut(BaseModel):
    status: str = "ok"


class HealthDetailedOut(BaseModel):
    database: str
    cache: str
    version: str
