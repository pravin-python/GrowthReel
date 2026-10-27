"""Request-id propagation for logging without threading `request` everywhere.

``RequestIDMiddleware`` sets the current request id into a contextvar as soon
as a request starts. Anything downstream — a service function, a Celery task
triggered synchronously, a log call deep in a selector — can read it back via
``get_request_id()`` without needing the ``HttpRequest`` passed down to it.
"""
import logging
import uuid
from contextvars import ContextVar

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"


def generate_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str) -> None:
    _request_id_ctx_var.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx_var.get()


class RequestIDLogFilter(logging.Filter):
    """Injects the current request id into every log record as `request_id`.

    Wired into ``LOGGING["filters"]`` in ``config/settings/base.py`` and
    attached to the console handler so the formatter can reference
    ``%(request_id)s``.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
