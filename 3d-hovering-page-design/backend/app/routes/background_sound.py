"""
Background Sound routes.

Allows tenants to configure per-agent ambient background sound for voice calls.
Configuration is stored in Agent.integrations['backgroundSound'].

GET  /api/background-sound/{agent_id}  — get current background sound config
PUT  /api/background-sound/{agent_id}  — update background sound config
GET  /api/background-sound/types       — list available ambient sound types
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Agent
from app.services.background_sound_service import AMBIENT_TYPES

logger = logging.getLogger("voiceflow.background_sound_routes")
router = APIRouter()


@router.get("/types")
async def list_ambient_types():
    """Return available ambient sound types with descriptions."""
    return {
        "types": [
            {
                "id": "none",
                "label": "None (Silence)",
                "description": "No background sound — quiet, professional, suited for scripted flows.",
            },
            {
                "id": "office",
                "label": "Office",
                "description": "Subtle office ambience — keyboard taps, occasional movement. Recommended default.",
                "recommendedVolume": 0.12,
            },
            {
                "id": "callcenter",
                "label": "Call Center",
                "description": "Light call center chatter — improves human perception & answer rates for outbound campaigns.",
                "recommendedVolume": 0.18,
            },
            {
                "id": "cafe",
                "label": "Café / Bistro",
                "description": "Relaxed café ambience with background music hum. Suits lifestyle & hospitality agents.",
                "recommendedVolume": 0.15,
            },
            {
                "id": "street",
                "label": "Street / Outdoor",
                "description": "Heavy outdoor noise simulation. Use only for testing adaptive noise cancellation tolerance.",
                "recommendedVolume": 0.10,
            },
        ]
    }


@router.get("/{agent_id}")
async def get_background_sound_config(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Return the current background sound configuration for an agent."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    integrations: dict = agent.integrations or {}
    cfg = integrations.get("backgroundSound", {"type": "none", "volume": 0.0})
    return {"agentId": agent_id, "backgroundSound": cfg}


@router.put("/{agent_id}")
async def update_background_sound_config(
    agent_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Update background sound config for an agent.

    Request body:
      { "type": "office", "volume": 0.15 }
    """
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    ambient_type = str(body.get("type", "none")).lower()
    if ambient_type not in AMBIENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type. Must be one of: {', '.join(AMBIENT_TYPES)}",
        )

    volume = float(body.get("volume", 0.15))
    volume = max(0.0, min(1.0, volume))

    integrations = dict(agent.integrations or {})
    integrations["backgroundSound"] = {"type": ambient_type, "volume": volume}
    agent.integrations = integrations

    await db.commit()
    logger.info(
        "[background_sound] agent=%s set type=%s volume=%.2f", agent_id, ambient_type, volume
    )
    return {"agentId": agent_id, "backgroundSound": integrations["backgroundSound"], "success": True}
