"""Tests for the identity app and the Django -> FastAPI bridge-JWT contract.

These are the automated counterpart to the manual verification performed
when this app was first built (see README.md "Verification performed") —
CI runs these on every push so the bridge contract can't silently drift.
"""
from __future__ import annotations

import jwt
import pytest
from django.conf import settings
from django.urls import reverse

from apps.users.models import User
from apps.users.services import issue_bridge_token, verify_password

pytestmark = pytest.mark.django_db


def test_create_user_hashes_password_and_sets_defaults():
    user = User.objects.create_user(email="member@example.com", password="s3cret-pass")

    assert user.password != "s3cret-pass"
    assert user.role == User.Role.MEMBER
    assert user.is_staff is False
    assert user.is_superuser is False
    assert verify_password(user, "s3cret-pass") is True
    assert verify_password(user, "wrong-password") is False


def test_create_superuser_sets_staff_and_superuser_flags():
    admin = User.objects.create_superuser(email="admin@example.com", password="s3cret-pass")

    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.role == User.Role.ADMIN


def test_issue_bridge_token_claims_match_contract():
    user = User.objects.create_user(
        email="staff@example.com", password="s3cret-pass", role=User.Role.STAFF
    )

    token = issue_bridge_token(user)
    claims = jwt.decode(token, settings.SHARED_JWT_SECRET, algorithms=["HS256"])

    assert claims["sub"] == str(user.pk)
    assert claims["email"] == user.email
    assert claims["role"] == "staff"
    assert claims["typ"] == "bridge"
    assert "jti" in claims
    assert claims["exp"] - claims["iat"] == settings.BRIDGE_JWT_TTL_SECONDS


def test_bridge_token_jti_is_recorded_in_cache():
    from django.core.cache import cache

    user = User.objects.create_user(email="jti@example.com", password="s3cret-pass")
    token = issue_bridge_token(user)
    claims = jwt.decode(token, settings.SHARED_JWT_SECRET, algorithms=["HS256"])

    assert cache.get(f"bridge-jti:{claims['jti']}") == 1


def test_login_success_redirects_to_bridge_callback_url(client):
    User.objects.create_user(email="login@example.com", password="s3cret-pass")

    response = client.post(
        reverse("users:login"),
        {"username": "login@example.com", "password": "s3cret-pass"},
    )

    assert response.status_code == 302
    assert response.url.startswith(f"{settings.APP_FRONTEND_URL}/auth/callback?token=")
    assert response.headers["Cache-Control"] == "no-store"


def test_login_failure_does_not_redirect(client):
    User.objects.create_user(email="login2@example.com", password="s3cret-pass")

    response = client.post(
        reverse("users:login"),
        {"username": "login2@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 200  # re-renders the form with an error
