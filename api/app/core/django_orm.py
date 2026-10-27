"""Bootstraps Django's ORM so this FastAPI process can import and use the
real `backend/` Django models and service functions in-process, against the
exact same database Django itself uses.

This is the core trick of the whole service: no HTTP calls to Django, ever.
`setup_django()` must run before any module does
`from apps.<app>.models import ...` or `from apps.<app>.services import ...`
— see `app/main.py`'s lifespan, which calls this before including any
router that touches Django models.
"""
from __future__ import annotations

import os
import sys

from app.core.config import settings

_initialized = False


def setup_django() -> None:
    """Idempotent: safe to call more than once (e.g. from tests)."""
    global _initialized
    if _initialized:
        return

    backend_dir = str(settings.BACKEND_DIR)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings.DJANGO_SETTINGS_MODULE)

    import django

    django.setup()

    _initialized = True
