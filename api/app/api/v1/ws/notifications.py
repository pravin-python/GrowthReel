"""WebSocket notifications demo endpoint.

Auth note: browsers cannot set custom headers on a WebSocket handshake, so
the access token travels as a `?token=` query parameter instead of an
`Authorization` header. This is the one place in the service that accepts a
bearer credential outside a header — documented here and in the README.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from asgiref.sync import sync_to_async
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import InvalidTokenError, decode_token
from app.core.ws_security_headers import get_ws_security_headers

logger = logging.getLogger("app")

router = APIRouter()

NOTIFICATION_INTERVAL_SECONDS = 15
# Not a registered WS close code, but in the private-use range (4000-4999)
# per RFC 6455 — used consistently for "bad/missing token" so the client can
# distinguish auth failures from a generic disconnect.
WS_UNAUTHORIZED_CODE = 4401


async def _authenticate(token: str | None):
    """Returns the Django User for a valid access token, or None."""
    if not token:
        return None

    try:
        claims = decode_token(token, expected_typ="access")
    except InvalidTokenError:
        return None

    from apps.users.models import User

    try:
        user = await sync_to_async(User.objects.get)(pk=claims.get("sub"))
    except (User.DoesNotExist, ValueError, TypeError):
        return None

    if not user.is_active:
        return None

    return user


@router.websocket("/ws/notifications")
async def notifications(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    user = await _authenticate(token)

    if user is None:
        # Close before accept()ing: the handshake itself fails rather than
        # completing and then immediately dropping the connection.
        await websocket.close(code=WS_UNAUTHORIZED_CODE)
        return

    await websocket.accept(headers=get_ws_security_headers())

    session_id = str(uuid.uuid4())
    await websocket.send_json({"type": "session.init", "session_id": session_id})

    try:
        counter = 0
        while True:
            # Wait for either a client message (we only care about a
            # disconnect) or the next tick of the notification timer,
            # whichever comes first, so a disconnect is noticed promptly
            # instead of only after the next ~15s tick.
            try:
                message = await asyncio.wait_for(
                    websocket.receive(), timeout=NOTIFICATION_INTERVAL_SECONDS
                )
            except asyncio.TimeoutError:
                counter += 1
                await websocket.send_json(
                    {
                        "type": "notification",
                        "message": f"You have a new update (#{counter}) for {user.email}",
                    }
                )
                continue

            if message.get("type") == "websocket.disconnect":
                break
            # Any other inbound client message is ignored — this is a simple
            # server-push demo channel, not a two-way protocol.
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws.notifications error for session_id=%s", session_id)
