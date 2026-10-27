"""Tests for shared, app-agnostic building blocks: the security headers and
request-id middleware, and the TimeStampedModel/SoftDeleteModel mixins.
"""
from __future__ import annotations

import uuid

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_security_headers_present_on_every_response(client):
    response = client.get(reverse("home"))

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_request_id_is_generated_and_echoed_back(client):
    response = client.get(reverse("home"))

    request_id = response.headers.get("X-Request-ID")
    assert request_id
    # Must be a real, unique identifier, not a static placeholder.
    uuid.UUID(request_id)


def test_request_id_is_echoed_when_client_supplies_one(client):
    incoming_id = str(uuid.uuid4())

    response = client.get(reverse("home"), HTTP_X_REQUEST_ID=incoming_id)

    assert response.headers["X-Request-ID"] == incoming_id


def test_admin_responses_are_never_cached(client):
    # `/admin/login/` (Django's own stock admin login, distinct from
    # `users:login`) exercises the generic `NO_STORE_PREFIXES` branch;
    # `users:login` sets its own stricter `Cache-Control: no-store` directly
    # (see test_login_success_redirects_to_bridge_callback_url in
    # apps/users/tests.py) and is covered there instead.
    response = client.get(reverse("admin:login"))

    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
