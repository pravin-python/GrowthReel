"""Shared FastAPI dependencies for the `/api/v1` routes."""
from __future__ import annotations

from asgiref.sync import sync_to_async
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import InvalidTokenError, decode_token

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
):
    """Extracts + validates the `Authorization: Bearer <access_token>` header
    and returns the real Django `User` row (loaded via the ORM, through
    `sync_to_async` since Django's ORM is sync and this app is async).

    Raises 401 on any failure: missing header, malformed/expired/wrong-typ
    token, or a user id that no longer resolves to an active user — the
    response never distinguishes which, to avoid leaking account existence.
    """
    # Imported lazily so this module can be imported before django.setup()
    # runs without crashing (routers are imported at app startup, before the
    # lifespan calls setup_django()).
    from apps.users.models import User

    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED

    try:
        claims = decode_token(credentials.credentials, expected_typ="access")
    except InvalidTokenError as exc:
        raise _UNAUTHORIZED from exc

    user_id = claims.get("sub")
    if not user_id:
        raise _UNAUTHORIZED

    try:
        user = await sync_to_async(User.objects.get)(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError) as exc:
        raise _UNAUTHORIZED from exc

    if not user.is_active:
        raise _UNAUTHORIZED

    return user
