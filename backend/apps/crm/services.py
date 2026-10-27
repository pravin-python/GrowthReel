"""Business logic for the CRM app."""
from __future__ import annotations

from typing import Any

from apps.crm.models import Client, Lead


def create_lead(*, name: str, email: str, **extra_fields: Any) -> Lead:
    lead = Lead.objects.create(name=name, email=email, **extra_fields)
    return lead


def change_lead_status(lead: Lead, status: str) -> Lead:
    if status not in Lead.Status.values:
        raise ValueError(f"Invalid lead status: {status!r}")
    lead.status = status
    lead.save(update_fields=["status", "updated_at"])
    return lead


def convert_lead_to_client(lead: Lead) -> Client:
    """Creates a Client from a Lead and marks the lead as won."""
    client = Client.objects.create(
        name=lead.company or lead.name,
        contact_email=lead.email,
        contact_phone=lead.phone,
    )
    change_lead_status(lead, Lead.Status.WON)
    return client
