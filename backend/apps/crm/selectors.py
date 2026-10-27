"""Read-only queries for the CRM app."""
from __future__ import annotations

from django.db.models import QuerySet

from apps.crm.models import Lead


def get_leads_for_owner(user) -> QuerySet[Lead]:
    return Lead.objects.filter(owner=user)


def get_open_leads() -> QuerySet[Lead]:
    return Lead.objects.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST])
