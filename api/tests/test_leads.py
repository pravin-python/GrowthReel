"""Tests for the leads endpoints — these must call the real
`apps.crm.services.change_lead_status`, not reimplement it, so a passing
PATCH test here proves the two services are genuinely wired together.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def lead(django_user):
    from apps.crm.services import create_lead

    return create_lead(name="Ada Lovelace", email="ada@example.com", company="Analytical Engines")


def test_list_leads_requires_auth(client):
    response = client.get("/api/v1/leads")

    assert response.status_code == 401


def test_list_leads_returns_created_lead(client, auth_headers, lead):
    response = client.get("/api/v1/leads", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == str(lead.pk) and item["email"] == "ada@example.com" for item in body)


def test_list_leads_filters_by_status(client, auth_headers, lead):
    response = client.get("/api/v1/leads", params={"status": "contacted"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_list_leads_rejects_invalid_status_filter(client, auth_headers):
    response = client.get("/api/v1/leads", params={"status": "bogus"}, headers=auth_headers)

    assert response.status_code == 400


def test_patch_lead_persists_via_real_django_service(client, auth_headers, lead):
    from apps.crm.models import Lead

    response = client.patch(
        f"/api/v1/leads/{lead.pk}", json={"status": "qualified"}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "qualified"

    lead.refresh_from_db()
    assert lead.status == Lead.Status.QUALIFIED


def test_patch_lead_rejects_invalid_status(client, auth_headers, lead):
    response = client.patch(
        f"/api/v1/leads/{lead.pk}", json={"status": "bogus"}, headers=auth_headers
    )

    assert response.status_code == 400


def test_patch_unknown_lead_returns_404(client, auth_headers):
    response = client.patch("/api/v1/leads/999999", json={"status": "contacted"}, headers=auth_headers)

    assert response.status_code == 404
