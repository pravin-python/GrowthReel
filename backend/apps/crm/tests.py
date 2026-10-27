"""Tests for CRM business logic (apps.crm.services) — the Django admin and
the FastAPI service both route lead mutations through these same functions,
so these tests are what protects both integrations from drifting.
"""
from __future__ import annotations

import pytest

from apps.crm.models import Lead
from apps.crm.services import change_lead_status, convert_lead_to_client, create_lead

pytestmark = pytest.mark.django_db


def test_create_lead_defaults_to_new_status():
    lead = create_lead(name="Ada Lovelace", email="ada@example.com", company="Analytical Engines")

    assert lead.status == Lead.Status.NEW
    assert lead.pk is not None


def test_change_lead_status_persists():
    lead = create_lead(name="Grace Hopper", email="grace@example.com")

    updated = change_lead_status(lead, Lead.Status.QUALIFIED)

    lead.refresh_from_db()
    assert updated.status == Lead.Status.QUALIFIED
    assert lead.status == Lead.Status.QUALIFIED


def test_change_lead_status_rejects_invalid_value():
    lead = create_lead(name="Bad Status", email="bad@example.com")

    with pytest.raises(ValueError):
        change_lead_status(lead, "not-a-real-status")


def test_convert_lead_to_client_marks_lead_won():
    lead = create_lead(
        name="Katherine Johnson", email="katherine@example.com", company="NASA", phone="555-0100"
    )

    client = convert_lead_to_client(lead)

    lead.refresh_from_db()
    assert lead.status == Lead.Status.WON
    assert client.name == "NASA"
    assert client.contact_email == "katherine@example.com"
    assert client.contact_phone == "555-0100"
