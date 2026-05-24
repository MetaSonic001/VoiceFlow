"""
IVR Tree routes — CRUD + Twilio voice handler.

GET  /api/ivr/                  — list IVR trees for tenant
POST /api/ivr/                  — create IVR tree
GET  /api/ivr/{tree_id}         — get IVR tree
PUT  /api/ivr/{tree_id}         — update IVR tree
DELETE /api/ivr/{tree_id}       — delete IVR tree

Twilio webhook routes (no auth, validated by Twilio signature):
GET/POST /voice/ivr/{tree_id}          — render root menu
GET/POST /voice/ivr/{tree_id}/gather   — handle DTMF digit + route
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import IVRTree
from app.services.ivr_service import render_gather_twiml, resolve_dtmf
from app.config import settings

logger = logging.getLogger("voiceflow.ivr_routes")
router = APIRouter()


def _validate_twilio_signature(request: Request, form_data: dict) -> bool:
    """Validate Twilio request signature. Returns True if valid or creds not configured."""
    auth_token = settings.TWILIO_AUTH_TOKEN
    if not auth_token:
        return True
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        proto = request.headers.get("x-forwarded-proto", "https")
        host = request.headers.get("host", "localhost")
        url = f"{proto}://{host}{request.url.path}"
        return validator.validate(url, form_data, signature)
    except Exception:
        logger.warning("[ivr] signature validation error — allowing request")
        return True


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_ivr_trees(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IVRTree)
        .where(IVRTree.tenantId == auth.tenant_id)
        .order_by(IVRTree.createdAt.desc())
    )
    trees = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "isActive": t.isActive,
            "phoneNumber": t.phoneNumber,
            "nodes": t.nodes,
            "createdAt": t.createdAt.isoformat() if t.createdAt else None,
        }
        for t in trees
    ]


@router.post("/")
async def create_ivr_tree(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    name = body.get("name")
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)
    tree = IVRTree(
        tenantId=auth.tenant_id,
        name=name,
        description=body.get("description"),
        nodes=body.get("nodes", []),
        isActive=body.get("isActive", True),
        phoneNumber=body.get("phoneNumber"),
    )
    db.add(tree)
    await db.commit()
    await db.refresh(tree)
    return JSONResponse(
        {"id": tree.id, "name": tree.name, "nodes": tree.nodes},
        status_code=201,
    )


@router.get("/{tree_id}")
async def get_ivr_tree(
    tree_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IVRTree).where(IVRTree.id == tree_id, IVRTree.tenantId == auth.tenant_id)
    )
    tree = result.scalar_one_or_none()
    if not tree:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return {"id": tree.id, "name": tree.name, "description": tree.description,
            "isActive": tree.isActive, "phoneNumber": tree.phoneNumber, "nodes": tree.nodes}


@router.put("/{tree_id}")
async def update_ivr_tree(
    tree_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IVRTree).where(IVRTree.id == tree_id, IVRTree.tenantId == auth.tenant_id)
    )
    tree = result.scalar_one_or_none()
    if not tree:
        return JSONResponse({"error": "Not found"}, status_code=404)
    for field in ("name", "description", "nodes", "isActive", "phoneNumber"):
        if field in body:
            setattr(tree, field, body[field])
    await db.commit()
    await db.refresh(tree)
    return {"id": tree.id, "name": tree.name, "nodes": tree.nodes}


@router.delete("/{tree_id}")
async def delete_ivr_tree(
    tree_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IVRTree).where(IVRTree.id == tree_id, IVRTree.tenantId == auth.tenant_id)
    )
    tree = result.scalar_one_or_none()
    if not tree:
        return JSONResponse({"error": "Not found"}, status_code=404)
    await db.delete(tree)
    await db.commit()
    return {"deleted": True}


# ── Twilio webhook handlers ───────────────────────────────────────────────────

@router.api_route("/voice/{tree_id}", methods=["GET", "POST"])
async def ivr_root(tree_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Render the root IVR menu TwiML."""
    form = await request.form()
    if not _validate_twilio_signature(request, dict(form)):
        return Response(content="Forbidden", status_code=403, media_type="text/plain")
    result = await db.execute(select(IVRTree).where(IVRTree.id == tree_id, IVRTree.isActive == True))
    tree = result.scalar_one_or_none()
    if not tree:
        return Response(
            content='<?xml version="1.0"?><Response><Say>This line is not configured.</Say><Hangup/></Response>',
            media_type="application/xml",
        )
    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", "localhost")
    base_url = f"{proto}://{host}"
    twiml = render_gather_twiml(tree, node_id="root", base_url=base_url)
    return Response(content=twiml, media_type="application/xml")


@router.api_route("/voice/{tree_id}/gather", methods=["GET", "POST"])
async def ivr_gather(tree_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Handle DTMF input and route to next node or agent."""
    form = await request.form()
    if not _validate_twilio_signature(request, dict(form)):
        return Response(content="Forbidden", status_code=403, media_type="text/plain")
    digit = str(form.get("Digits", "")).strip()
    node_id = str(request.query_params.get("node", "root"))

    result = await db.execute(select(IVRTree).where(IVRTree.id == tree_id, IVRTree.isActive == True))
    tree = result.scalar_one_or_none()
    if not tree:
        return Response(
            content='<?xml version="1.0"?><Response><Say>Configuration error.</Say><Hangup/></Response>',
            media_type="application/xml",
        )

    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", "localhost")
    base_url = f"{proto}://{host}"

    twiml, agent_id = await resolve_dtmf(tree, node_id, digit, db, base_url)
    if agent_id:
        logger.info("[ivr] routed to agent %s via IVR tree %s", agent_id, tree_id)
    return Response(content=twiml, media_type="application/xml")
