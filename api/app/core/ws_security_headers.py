"""The literal security header set applied to the WebSocket 101 (Switching
Protocols) response, equivalent to `SecurityHeadersMiddleware` for HTTP.

Starlette's `WebSocket.accept()` takes a `headers` argument (list of
`(bytes, bytes)` tuples) that gets attached to the 101 response the ASGI
server sends during the handshake — this is the only place extra headers can
be added to a WebSocket upgrade response, since there is no "response
object" to mutate afterwards the way there is for a normal HTTP response.
"""
from __future__ import annotations

from app.core.config import settings

_BASE_WS_SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
    (b"x-xss-protection", b"1; mode=block"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"),
]


def get_ws_security_headers() -> list[tuple[bytes, bytes]]:
    headers = list(_BASE_WS_SECURITY_HEADERS)
    if settings.is_production:
        headers.append(
            (
                b"strict-transport-security",
                b"max-age=31536000; includeSubDomains; preload",
            )
        )
    return headers
