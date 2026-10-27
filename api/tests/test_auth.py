"""Tests for the Django-login -> FastAPI bridge and this service's own
session lifecycle. `bridge_token` is minted via the REAL
`apps.users.services.issue_bridge_token` (see conftest.py), exactly as the
real Django login view would produce it — not a hand-rolled stand-in.
"""
from __future__ import annotations

import jwt


def test_exchange_valid_bridge_token_returns_access_token_and_sets_cookie(client, bridge_token):
    response = client.post("/api/v1/auth/exchange", json={"bridge_token": bridge_token})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert "access_token" in body
    assert "refresh_token" in response.cookies


def test_exchange_rejects_garbage_token(client):
    response = client.post("/api/v1/auth/exchange", json={"bridge_token": "not-a-real-jwt"})

    assert response.status_code == 401


def test_exchange_rejects_expired_token(client, django_user):
    from datetime import datetime, timedelta, timezone

    from app.core.config import settings

    expired_claims = {
        "sub": str(django_user.pk),
        "email": django_user.email,
        "role": django_user.role,
        "jti": "expired-jti",
        "iat": datetime.now(tz=timezone.utc) - timedelta(seconds=120),
        "exp": datetime.now(tz=timezone.utc) - timedelta(seconds=60),
        "typ": "bridge",
    }
    expired_token = jwt.encode(expired_claims, settings.SHARED_JWT_SECRET, algorithm="HS256")

    response = client.post("/api/v1/auth/exchange", json={"bridge_token": expired_token})

    assert response.status_code == 401


def test_exchange_rejects_wrong_token_type(client, django_user):
    from app.core.security import create_access_token

    # An access token is validly signed but has typ="access", not "bridge".
    access_token = create_access_token(django_user)

    response = client.post("/api/v1/auth/exchange", json={"bridge_token": access_token})

    assert response.status_code == 401


def test_me_requires_bearer_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client, auth_headers, django_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(django_user.pk)
    assert body["email"] == django_user.email
    assert body["role"] == django_user.role


def test_refresh_without_cookie_is_rejected(client):
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


def test_refresh_with_valid_cookie_issues_new_access_token(client, bridge_token):
    exchange_response = client.post("/api/v1/auth/exchange", json={"bridge_token": bridge_token})
    first_access_token = exchange_response.json()["access_token"]

    refresh_response = client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    new_access_token = refresh_response.json()["access_token"]
    assert new_access_token != first_access_token


def test_logout_clears_cookie_and_returns_204(client, bridge_token):
    client.post("/api/v1/auth/exchange", json={"bridge_token": bridge_token})

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert client.cookies.get("refresh_token") is None


def test_unhandled_exception_returns_generic_json_with_security_headers(client, auth_headers):
    # A non-numeric lead id exercises the normalized-to-404 path in
    # leads.py; a genuinely unhandled exception is harder to trigger without
    # a dedicated debug route (which the real service deliberately doesn't
    # ship — see api/README.md "Verification" step 10 for how that was
    # exercised manually instead). This at least proves no raw Django/ASGI
    # traceback or internal message ever reaches the client on a bad input.
    response = client.patch(
        "/api/v1/leads/not-a-number", json={"status": "contacted"}, headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Lead not found"}
