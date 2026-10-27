"""FastAPI application entrypoint.

`setup_django()` is called from the `lifespan` context below, which runs
once at app startup, *before* uvicorn starts accepting any requests. Every
route in this service lazy-imports its Django models/services inside its
own function body rather than at module level (see e.g.
`app/api/v1/deps.py`, `app/api/v1/routes/leads.py`) specifically so that
importing this module (and the routers it includes) never touches Django
before `django.setup()` has run — the lifespan hook is what guarantees that
ordering for real traffic.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.django_orm import setup_django
from app.core.middleware import (
    REQUEST_ID_HEADER,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    apply_security_headers,
    get_request_id,
)

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_django()
    yield


app = FastAPI(title="GrowthReel API", version="1.0.0", lifespan=lifespan)

# Order matters: Starlette applies middleware outer-to-inner in the reverse
# of the order added here. CORS is added last (outermost) so it sees the
# request earliest and the response latest.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(StarletteHTTPException)
async def handled_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Explicit HTTPExceptions raised by our own routes (401/404/400/...) are
    # already safe, intentional, non-leaky responses — pass them through
    # unchanged rather than flattening them into the generic 500 handler.
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """VAPT fix #13: never leak a traceback or exception message to the
    client. Applied unconditionally (not just when `ENV=="production"`) for
    consistency — local dev should see the same response shape production
    does; the full exception (with the request id) still goes to the server
    log either way, so nothing is lost for local debugging.
    """
    request_id = get_request_id()
    logger.exception("unhandled exception for request_id=%s", request_id)
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "request_id": request_id},
    )
    # This response is built by Starlette's ServerErrorMiddleware, which
    # wraps OUTSIDE every middleware added via app.add_middleware() below —
    # so it never passes back through SecurityHeadersMiddleware/
    # RequestIDMiddleware the normal way. Apply both by hand so a 500 is
    # never the one response missing them. See apply_security_headers()'s
    # docstring for the full explanation; verified live (README.md
    # "Verification" step 10).
    apply_security_headers(response)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
