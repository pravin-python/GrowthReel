"""Lead endpoints. All mutation goes through the real
`apps.crm.services.change_lead_status` — this router never reimplements
that logic, it only calls it (via `sync_to_async`, since Django's ORM and
service functions are sync and this app is async).
"""
from __future__ import annotations

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import LeadOut, LeadStatusUpdate

router = APIRouter()


def _lead_to_out(lead) -> LeadOut:
    return LeadOut(
        id=str(lead.pk),
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        status=lead.status,
        source=lead.source,
        owner_id=str(lead.owner_id) if lead.owner_id else None,
        created_at=lead.created_at,
    )


def _list_leads_sync(status_filter: str | None) -> list:
    from apps.crm.models import Lead

    qs = Lead.objects.all()
    if status_filter is not None:
        qs = qs.filter(status=status_filter)
    return list(qs)


def _patch_lead_sync(lead_id: str, new_status: str):
    from apps.crm.models import Lead
    from apps.crm.services import change_lead_status

    try:
        lead = Lead.objects.get(pk=lead_id)
    except (Lead.DoesNotExist, ValueError, TypeError) as exc:
        # A non-numeric `lead_id` (Lead's pk is a plain integer) raises
        # ValueError/TypeError from Django's own field-conversion code, which
        # carries an internal, implementation-specific message
        # (e.g. "Field 'id' expected a number but got '...'") — never worth
        # exposing to the client. Normalize every "couldn't find this lead"
        # case to a single, generic DoesNotExist so the route layer always
        # returns a plain 404.
        raise Lead.DoesNotExist from exc

    return change_lead_status(lead, new_status)


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    user=Depends(get_current_user),
) -> list[LeadOut]:
    from apps.crm.models import Lead

    if status_filter is not None and status_filter not in Lead.Status.values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lead status: {status_filter!r}",
        )

    leads = await sync_to_async(_list_leads_sync)(status_filter)
    return [_lead_to_out(lead) for lead in leads]


@router.patch("/leads/{lead_id}", response_model=LeadOut)
async def patch_lead(
    lead_id: str,
    body: LeadStatusUpdate,
    user=Depends(get_current_user),
) -> LeadOut:
    from apps.crm.models import Lead

    if body.status not in Lead.Status.values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lead status: {body.status!r}",
        )

    try:
        lead = await sync_to_async(_patch_lead_sync)(lead_id, body.status)
    except Lead.DoesNotExist as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _lead_to_out(lead)
