"""
/api/dnd — Do-Not-Disturb registry.

POST   /api/dnd/           — Add a number to DND
DELETE /api/dnd/{id}       — Remove a number from DND
GET    /api/dnd/           — List DND numbers (paginated)
POST   /api/dnd/bulk       — Upload CSV of DND numbers
"""
from __future__ import annotations

import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import DNDRegistry

logger = logging.getLogger("voiceflow.dnd")
router = APIRouter()


@router.post("/")
async def add_dnd(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Add a phone number to the DND registry."""
    body = await request.json()
    phone = (body.get("phoneNumber") or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phoneNumber is required")

    # Normalise to E.164 if phonenumbers is available
    phone = _normalize_phone(phone)

    existing = await db.execute(
        select(DNDRegistry).where(
            DNDRegistry.tenantId == auth.tenant_id,
            DNDRegistry.phoneNumber == phone,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Number already on DND list")

    entry = DNDRegistry(
        tenantId=auth.tenant_id,
        phoneNumber=phone,
        reason=body.get("reason"),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _dnd_to_dict(entry)


@router.delete("/{dnd_id}")
async def remove_dnd(
    dnd_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a number from the DND registry."""
    result = await db.execute(
        select(DNDRegistry).where(
            DNDRegistry.id == dnd_id,
            DNDRegistry.tenantId == auth.tenant_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="DND entry not found")
    await db.delete(entry)
    await db.commit()
    return {"status": "removed", "id": dnd_id}


@router.get("/")
async def list_dnd(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of DND numbers for the tenant."""
    offset = (page - 1) * limit
    total_result = await db.execute(
        select(func.count()).where(DNDRegistry.tenantId == auth.tenant_id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(DNDRegistry)
        .where(DNDRegistry.tenantId == auth.tenant_id)
        .order_by(DNDRegistry.createdAt.desc())
        .offset(offset)
        .limit(limit)
    )
    entries = result.scalars().all()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "entries": [_dnd_to_dict(e) for e in entries],
    }


@router.post("/bulk")
async def bulk_add_dnd(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV file of DND numbers.

    Required column: phone_number
    Optional column: reason
    """
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames or "phone_number" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV must contain a 'phone_number' column")

    added = 0
    skipped = 0

    # Fetch existing numbers to avoid duplicates
    existing_result = await db.execute(
        select(DNDRegistry.phoneNumber).where(DNDRegistry.tenantId == auth.tenant_id)
    )
    existing_phones = {row[0] for row in existing_result.all()}

    for row in reader:
        phone = (row.get("phone_number") or "").strip()
        if not phone:
            skipped += 1
            continue
        phone = _normalize_phone(phone)
        if phone in existing_phones:
            skipped += 1
            continue
        entry = DNDRegistry(
            tenantId=auth.tenant_id,
            phoneNumber=phone,
            reason=(row.get("reason") or "").strip() or None,
        )
        db.add(entry)
        existing_phones.add(phone)
        added += 1

    await db.commit()
    logger.info("[dnd] bulk upload tenant=%s added=%d skipped=%d", auth.tenant_id, added, skipped)
    return {"added": added, "skipped": skipped}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 if phonenumbers library is available."""
    try:
        import phonenumbers
        parsed = phonenumbers.parse(phone, "IN")  # default region India
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return phone


def _dnd_to_dict(entry: DNDRegistry) -> dict:
    return {
        "id": entry.id,
        "tenantId": entry.tenantId,
        "phoneNumber": entry.phoneNumber,
        "reason": entry.reason,
        "createdAt": entry.createdAt.isoformat() if entry.createdAt else None,
    }
