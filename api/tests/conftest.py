"""Test setup for the FastAPI service's own pytest suite.

Unlike the manual `scripts/verify_*.py` tools used while first building this
service (which ran against the real backend dev DB), these tests run against
a disposable SQLite file DB, created fresh per test session by calling
Django's own `migrate` management command directly — no `pytest-django`
dependency needed here, since this service only ever touches Django through
`django.setup()` + the ORM, the same way it does in production.

A real file (not `:memory:`) is used deliberately: `sync_to_async` calls can
run on a different OS thread than the one that opened the connection, and
SQLite's `:memory:` database is private to the connection that created it —
a second thread opening its own connection to `:memory:` would see an empty,
unrelated database. Pointing everything at the same file sidesteps that
entirely, however many threads end up involved.
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = (API_ROOT.parent / "backend").resolve()

# Must be set before anything imports `app.core.config` (which builds the
# `settings` singleton at import time) — env vars here win over `api/.env`.
os.environ.setdefault("BACKEND_DIR", str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.testing")
os.environ.setdefault("SHARED_JWT_SECRET", "test-only-shared-jwt-secret-0123456789abcdef")
os.environ.setdefault("APP_FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
# "local" (not "production"): skips the Redis-backed bridge-jti replay check
# and refresh revocation list (see app/core/redis_client.py) so this suite
# needs no Redis server, exactly like the backend's own local dev setup.
os.environ.setdefault("ENV", "local")

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.django_orm import setup_django  # noqa: E402

setup_django()

from django.conf import settings as django_settings  # noqa: E402
from django.core.management import call_command  # noqa: E402

_test_db_path = Path(tempfile.gettempdir()) / f"growthreel_api_test_{uuid.uuid4().hex}.sqlite3"
django_settings.DATABASES["default"]["NAME"] = str(_test_db_path)
call_command("migrate", run_syncdb=True, verbosity=0)

from app.main import app  # noqa: E402  (import only after setup_django() + migrate)


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    from django.db import connections

    connections.close_all()
    try:
        _test_db_path.unlink(missing_ok=True)
    except OSError:
        # Windows can still hold the file open briefly after close_all();
        # it's in the OS temp dir, so leaking one file here is harmless.
        pass


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def django_user(request):
    from apps.users.models import User

    email = f"{uuid.uuid4().hex}@example.com"
    return User.objects.create_user(email=email, password="s3cret-pass")


@pytest.fixture()
def bridge_token(django_user):
    from apps.users.services import issue_bridge_token

    return issue_bridge_token(django_user)


@pytest.fixture()
def access_token(client, bridge_token):
    response = client.post("/api/v1/auth/exchange", json={"bridge_token": bridge_token})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}
