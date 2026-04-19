"""
/api/webhooks routes — webhook endpoint management.

POST   /api/webhooks/          Register a new webhook endpoint
GET    /api/webhooks/          List all webhook endpoints
DELETE /api/webhooks/{id}      Remove a webhook endpoint
GET    /api/webhooks/schema    Return OpenAPI-compatible event schema for n8n/Zapier
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import WebhookEndpoint
from app.services.webhook_service import SUPPORTED_EVENTS

logger = logging.getLogger("voiceflow.webhooks")
router = APIRouter()


# ── Serialiser ────────────────────────────────────────────────────────────────

def _endpoint_to_dict(ep: WebhookEndpoint) -> dict:
    return {
        "id": ep.id,
        "tenantId": ep.tenantId,
        "url": ep.url,
        "events": ep.events,
        "isActive": ep.isActive,
        "description": ep.description,
        "createdAt": ep.createdAt.isoformat() if ep.createdAt else None,
        "updatedAt": ep.updatedAt.isoformat() if ep.updatedAt else None,
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("/")
async def create_webhook(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Register a new webhook endpoint."""
    body = await request.json()

    url: str = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    events = body.get("events", [])
    if isinstance(events, str):
        events = [e.strip() for e in events.split(",") if e.strip()]
    if not events:
        raise HTTPException(status_code=400, detail="at least one event is required")

    invalid = [e for e in events if e not in SUPPORTED_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported events: {invalid}. Supported: {sorted(SUPPORTED_EVENTS)}",
        )

    endpoint = WebhookEndpoint(
        tenantId=auth.tenant_id,
        url=url,
        events=events,
        description=body.get("description"),
        isActive=body.get("isActive", True),
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return _endpoint_to_dict(endpoint)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_webhooks(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.tenantId == auth.tenant_id)
        .order_by(WebhookEndpoint.createdAt.desc())
    )
    return {"webhooks": [_endpoint_to_dict(ep) for ep in result.scalars().all()]}


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.tenantId == auth.tenant_id,
        )
    )
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    await db.delete(ep)
    await db.commit()
    return {"deleted": True}


# ── Schema (for n8n / Zapier import) ─────────────────────────────────────────

@router.get("/schema")
async def webhook_schema():
    """
    Return an OpenAPI-compatible fragment describing the webhook payload schema.
    Used by n8n, Zapier, and other automation platforms to import trigger definitions.
    """
    event_schemas = {}
    for event in sorted(SUPPORTED_EVENTS):
        event_schemas[event] = {
            "description": _EVENT_DESCRIPTIONS.get(event, event),
            "payload": _EVENT_PAYLOADS.get(event, {"type": "object", "properties": {}}),
        }

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "VoiceFlow Webhooks",
            "version": "1.0.0",
            "description": "Outbound webhook events fired by VoiceFlow",
        },
        "paths": {
            "/webhook": {
                "post": {
                    "summary": "VoiceFlow webhook delivery",
                    "description": "Payload POSTed to your endpoint on each event",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        {"$ref": f"#/components/schemas/{_event_to_schema_name(e)}"}
                                        for e in sorted(SUPPORTED_EVENTS)
                                    ]
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Acknowledged"}},
                }
            }
        },
        "components": {
            "schemas": {
                _event_to_schema_name(event): {
                    "type": "object",
                    "required": ["event", "tenantId"],
                    "properties": {
                        "event": {"type": "string", "enum": [event]},
                        "tenantId": {"type": "string"},
                        **info["payload"].get("properties", {}),
                    },
                }
                for event, info in event_schemas.items()
            }
        },
        "events": event_schemas,
        "security": [
            {
                "note": "Each request includes X-VoiceFlow-Signature: sha256=<hmac>",
                "algorithm": "HMAC-SHA256",
                "header": "X-VoiceFlow-Signature",
            }
        ],
    }


# ── Schema helpers ────────────────────────────────────────────────────────────

def _event_to_schema_name(event: str) -> str:
    """Convert 'call.completed' → 'CallCompletedEvent'."""
    return "".join(p.capitalize() for p in event.replace(".", "_").split("_")) + "Event"


_EVENT_DESCRIPTIONS = {
    "call.completed": "Fired when a voice call ends.",
    "campaign.finished": "Fired when all contacts in a campaign have been processed.",
    "escalation.triggered": "Fired when an agent escalation rule matches.",
    "retraining.flagged": "Fired when a call is flagged for agent retraining.",
}

_EVENT_PAYLOADS: dict[str, dict] = {
    "call.completed": {
        "type": "object",
        "properties": {
            "callSid": {"type": "string", "description": "Twilio Call SID"},
            "agentId": {"type": "string"},
            "durationSeconds": {"type": "integer"},
            "callerPhone": {"type": "string"},
        },
    },
    "campaign.finished": {
        "type": "object",
        "properties": {
            "campaignId": {"type": "string"},
            "campaignName": {"type": "string"},
            "totalDialed": {"type": "integer"},
            "answeredCount": {"type": "integer"},
        },
    },
    "escalation.triggered": {
        "type": "object",
        "properties": {
            "agentId": {"type": "string"},
            "sessionId": {"type": "string"},
            "trigger": {"type": "string"},
            "transcript": {"type": "string"},
        },
    },
    "retraining.flagged": {
        "type": "object",
        "properties": {
            "callLogId": {"type": "string"},
            "agentId": {"type": "string"},
            "reason": {"type": "string"},
        },
    },
}
