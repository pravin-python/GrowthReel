"""Cross-cutting HTTP middleware: request-id propagation and security headers."""
import logging

from django.utils.deprecation import MiddlewareMixin

from apps.core.context import REQUEST_ID_HEADER, generate_request_id, set_request_id

logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """Generates (or propagates) an `X-Request-ID` for every request.

    - If the incoming request already carries an `X-Request-ID` header
      (e.g. set by an upstream proxy/load balancer), it is reused.
    - Otherwise a fresh uuid4 hex is generated.
    - The id is stored on `request.request_id`, pushed into the
      `apps.core.context` contextvar (so logging can pick it up without the
      request object being passed around), and echoed back on the response.
    """

    def process_request(self, request):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming or generate_request_id()
        request.request_id = request_id
        set_request_id(request_id)
        logger.info("request.start %s %s", request.method, request.path)

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response[REQUEST_ID_HEADER] = request_id
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Applies a hardened-but-working set of security headers to responses.

    Design decision (documented in README too): the original spec called for
    `default-src 'none'; frame-ancestors 'none'; base-uri 'none'` everywhere.
    That literal policy is correct and is what the FastAPI JSON/WebSocket
    side should use as-is (it never renders HTML/CSS/JS, so there's nothing
    for `'none'` to break). This Django app DOES render HTML/CSS/JS
    (Tailwind-styled templates, the login page, the admin), so a blanket
    `'none'` would break its own static assets and inline-free scripts. We
    keep `frame-ancestors 'none'` (nothing may frame this site — same
    intent as the spec) and relax the rest to `'self'` (plus `data:` for
    images/fonts and `'unsafe-inline'` for style, which the Django admin
    requires), which preserves "no framing, no cross-origin anything" while
    letting the site actually render.
    """

    CSP = (
        "default-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self' data:"
    )

    NO_STORE_PREFIXES = ("/admin/", "/accounts/")

    def process_response(self, request, response):
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "no-referrer"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Content-Security-Policy"] = self.CSP

        if request.is_secure():
            response["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Login view and anything carrying the bridge-JWT redirect must never
        # be cached by the browser or an intermediary proxy.
        if getattr(request, "_growthreel_no_store", False):
            response["Cache-Control"] = "no-store"
        elif request.path.startswith(self.NO_STORE_PREFIXES):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response
