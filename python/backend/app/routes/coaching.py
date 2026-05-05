"""
Coaching Card routes — AI Call Coach approval workflow.

When analyze_call() produces coaching insights, they are stored as
CoachingCard rows. Tenant admins review, approve, or reject them here.
Approved cards are automatically merged into the agent's systemPrompt.

GET  /api/coaching/                         — list pending coaching cards
GET  /api/coaching/{card_id}                — get card detail
POST /api/coaching/{card_id}/approve        — approve and merge into agent prompt
POST /api/coaching/{card_id}/reject         — reject a card
GET  /api/coaching/agents/{agent_id}/report — full coaching report for an agent
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import CoachingCard, Agent

logger = logging.getLogger("voiceflow.coaching_routes")
router = APIRouter()


def _card_dict(c: CoachingCard) -> dict:
    return {
        "id": c.id,
        "agentId": c.agentId,
        "callLogId": c.callLogId,
        "status": c.status,
        "observation": c.observation,
        "suggestedPromptDelta": c.suggestedPromptDelta,
        "impactScore": c.impactScore,
        "approvedBy": c.approvedBy,
        "approvedAt": c.approvedAt.isoformat() if c.approvedAt else None,
        "appliedAt": c.appliedAt.isoformat() if c.appliedAt else None,
        "createdAt": c.createdAt.isoformat() if c.createdAt else None,
    }


@router.get("/")
async def list_coaching_cards(
    status: str | None = None,
    agent_id: str | None = None,
    limit: int = 50,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    where = [CoachingCard.tenantId == auth.tenant_id]
    if status:
        where.append(CoachingCard.status == status)
    if agent_id:
        where.append(CoachingCard.agentId == agent_id)
    result = await db.execute(
        select(CoachingCard).where(*where)
        .order_by(CoachingCard.createdAt.desc())
        .limit(limit)
    )
    cards = result.scalars().all()
    return [_card_dict(c) for c in cards]


@router.get("/{card_id}")
async def get_coaching_card(
    card_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CoachingCard).where(CoachingCard.id == card_id, CoachingCard.tenantId == auth.tenant_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return _card_dict(card)


@router.post("/{card_id}/approve")
async def approve_coaching_card(
    card_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a coaching card and automatically merge the suggestedPromptDelta
    into the agent's systemPrompt.  The delta is appended as a new instruction block.
    """
    card_result = await db.execute(
        select(CoachingCard).where(CoachingCard.id == card_id, CoachingCard.tenantId == auth.tenant_id)
    )
    card = card_result.scalar_one_or_none()
    if not card:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if card.status != "pending":
        return JSONResponse({"error": f"Card is already {card.status}"}, status_code=400)

    # Merge the prompt delta into the agent's system prompt
    agent_result = await db.execute(
        select(Agent).where(Agent.id == card.agentId, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    if card.suggestedPromptDelta:
        current_prompt = agent.systemPrompt or ""
        separator = "\n\n--- Coaching Card Applied ---\n"
        agent.systemPrompt = current_prompt + separator + card.suggestedPromptDelta
        card.appliedAt = datetime.now(timezone.utc)

    card.status = "approved"
    card.approvedBy = auth.user_id
    card.approvedAt = datetime.now(timezone.utc)
    await db.commit()

    logger.info("[coaching] card %s approved and applied to agent %s", card_id, card.agentId)
    return {
        "status": "approved",
        "applied": bool(card.suggestedPromptDelta),
        "agentId": card.agentId,
    }


@router.post("/{card_id}/reject")
async def reject_coaching_card(
    card_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    card_result = await db.execute(
        select(CoachingCard).where(CoachingCard.id == card_id, CoachingCard.tenantId == auth.tenant_id)
    )
    card = card_result.scalar_one_or_none()
    if not card:
        return JSONResponse({"error": "Not found"}, status_code=404)
    card.status = "rejected"
    card.approvedBy = auth.user_id
    await db.commit()
    return {"status": "rejected"}


@router.get("/agents/{agent_id}/report")
async def get_coaching_report(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Full coaching history for an agent with stats."""
    result = await db.execute(
        select(CoachingCard).where(
            CoachingCard.agentId == agent_id,
            CoachingCard.tenantId == auth.tenant_id,
        ).order_by(CoachingCard.createdAt.desc())
    )
    cards = result.scalars().all()
    pending = [c for c in cards if c.status == "pending"]
    approved = [c for c in cards if c.status == "approved"]
    rejected = [c for c in cards if c.status == "rejected"]
    avg_impact = (
        sum(c.impactScore for c in approved if c.impactScore) / len([c for c in approved if c.impactScore])
        if any(c.impactScore for c in approved) else None
    )
    return {
        "agent_id": agent_id,
        "total": len(cards),
        "pending": len(pending),
        "approved": len(approved),
        "rejected": len(rejected),
        "avg_impact_score": round(avg_impact, 3) if avg_impact else None,
        "cards": [_card_dict(c) for c in cards[:20]],  # last 20
    }
