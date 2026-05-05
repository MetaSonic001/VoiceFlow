"""
/api/contacts routes — OmniCRM built-in contact manager.

Each tenant has a contacts database where call history, extracted variables,
lead scores, and conversation summaries accumulate over time.
When the same number calls back, the agent has historical context automatically.

GET    /api/contacts/                     — list contacts with filters
POST   /api/contacts/                     — create/upsert contact
GET    /api/contacts/{contact_id}         — get contact detail
PUT    /api/contacts/{contact_id}         — update contact
DELETE /api/contacts/{contact_id}         — delete contact
GET    /api/contacts/lookup/{phone}       — look up by phone number (used pre-call)
POST   /api/contacts/{contact_id}/note    — add a note to a contact
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Contact

logger = logging.getLogger("voiceflow.contacts_routes")
router = APIRouter()


def _contact_dict(c: Contact, include_extracted: bool = False) -> dict:
    d = {
        "id": c.id,
        "phoneNumber": c.phoneNumber,
        "name": c.name,
        "email": c.email,
        "company": c.company,
        "intentLevel": c.intentLevel,
        "sentiment": c.sentiment,
        "totalCalls": c.totalCalls,
        "lastCalledAt": c.lastCalledAt.isoformat() if c.lastCalledAt else None,
        "hubspotContactId": c.hubspotContactId,
        "salesforceLeadId": c.salesforceLeadId,
        "tags": c.tags,
        "notes": c.notes,
        "createdAt": c.createdAt.isoformat() if c.createdAt else None,
        "updatedAt": c.updatedAt.isoformat() if c.updatedAt else None,
    }
    if include_extracted:
        d["extractedData"] = c.extractedData
        d["crmContext"] = c.crmContext
    return d


@router.get("/")
async def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    intent_level: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    where = [Contact.tenantId == auth.tenant_id]
    if search:
        like = f"%{search}%"
        where.append(or_(
            Contact.name.ilike(like),
            Contact.phoneNumber.ilike(like),
            Contact.email.ilike(like),
            Contact.company.ilike(like),
        ))
    if intent_level:
        where.append(Contact.intentLevel == intent_level)

    total = (await db.execute(select(func.count(Contact.id)).where(*where))).scalar() or 0
    result = await db.execute(
        select(Contact).where(*where)
        .order_by(Contact.lastCalledAt.desc().nullslast())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    contacts = result.scalars().all()
    return {
        "contacts": [_contact_dict(c) for c in contacts],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/lookup/{phone}")
async def lookup_by_phone(
    phone: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Look up a contact by phone number.  Used by the voice handler before each call
    to inject caller context into the agent's system prompt.
    """
    result = await db.execute(
        select(Contact).where(Contact.tenantId == auth.tenant_id, Contact.phoneNumber == phone)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return JSONResponse({"found": False, "contact": None})
    return {"found": True, "contact": _contact_dict(contact, include_extracted=True)}


@router.get("/{contact_id}")
async def get_contact(
    contact_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenantId == auth.tenant_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return _contact_dict(contact, include_extracted=True)


@router.post("/")
async def create_or_upsert_contact(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a contact or upsert by phone number if it already exists."""
    phone = (body.get("phoneNumber") or "").strip()
    if not phone:
        return JSONResponse({"error": "phoneNumber is required"}, status_code=400)

    # Upsert by phone
    result = await db.execute(
        select(Contact).where(Contact.tenantId == auth.tenant_id, Contact.phoneNumber == phone)
    )
    contact = result.scalar_one_or_none()

    if contact is None:
        contact = Contact(tenantId=auth.tenant_id, phoneNumber=phone)
        db.add(contact)
        is_new = True
    else:
        is_new = False

    for field in ("name", "email", "company", "intentLevel", "sentiment",
                  "tags", "notes", "hubspotContactId", "salesforceLeadId",
                  "crmContext", "extractedData"):
        if field in body:
            setattr(contact, field, body[field])

    contact.updatedAt = datetime.now(timezone.utc)  # type: ignore[assignment]
    await db.commit()
    await db.refresh(contact)
    return JSONResponse(_contact_dict(contact), status_code=201 if is_new else 200)


@router.put("/{contact_id}")
async def update_contact(
    contact_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenantId == auth.tenant_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return JSONResponse({"error": "Not found"}, status_code=404)

    for field in ("name", "email", "company", "intentLevel", "sentiment",
                  "tags", "notes", "hubspotContactId", "salesforceLeadId"):
        if field in body:
            setattr(contact, field, body[field])

    contact.updatedAt = datetime.now(timezone.utc)  # type: ignore[assignment]
    await db.commit()
    await db.refresh(contact)
    return _contact_dict(contact)


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenantId == auth.tenant_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return JSONResponse({"error": "Not found"}, status_code=404)
    await db.delete(contact)
    await db.commit()
    return {"deleted": True}


@router.post("/{contact_id}/note")
async def add_note(
    contact_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Append a timestamped note to a contact."""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenantId == auth.tenant_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return JSONResponse({"error": "Not found"}, status_code=404)

    note_text = (body.get("note") or "").strip()
    if not note_text:
        return JSONResponse({"error": "note is required"}, status_code=400)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_entry = f"[{timestamp}] {note_text}"
    existing = contact.notes or ""
    contact.notes = f"{existing}\n{new_entry}".strip()
    contact.updatedAt = datetime.now(timezone.utc)  # type: ignore[assignment]
    await db.commit()
    return {"note": new_entry, "notes": contact.notes}
