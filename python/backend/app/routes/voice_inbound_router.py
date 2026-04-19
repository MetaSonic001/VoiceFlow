"""
/api/voice inbound router — delegates to the correct telephony handler
based on the agent's telephony_provider field.

  twilio-gather  → voice.py inbound handler (old Gather loop, direct call)
  twilio-stream  → voice_twilio_stream.handle_inbound_call (Media Streams)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.database import AsyncSessionLocal
from app.models import Agent
from app.services.rag_service import process_query

logger = logging.getLogger("voiceflow.inbound_router")
router = APIRouter()


@router.post("/inbound/{agent_id}")
async def inbound_router(agent_id: str, request: Request) -> Response:
    """Route to the correct telephony handler for this agent."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

    if not agent:
        resp = VoiceResponse()
        resp.say("Agent not found.")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    provider = (agent.telephony_provider or "twilio-gather").lower()

    if provider == "twilio-stream":
        from app.routes.voice_twilio_stream import handle_inbound_call

        return await handle_inbound_call(agent, request)

    if provider in ("twilio-gather", "twilio"):
        # Twilio Gather loop — greet and collect speech
        agent_name = agent.name or "your AI assistant"
        resp = VoiceResponse()
        gather = Gather(
            input="speech",
            action=f"/api/voice/gather/{agent_id}",
            method="POST",
            speech_timeout="auto",
            language="en-US",
        )
        gather.say(
            f"Hello, you've reached {agent_name}. How can I help you today?",
            voice="Polly.Joanna",
        )
        resp.append(gather)
        resp.say("I didn't hear anything. Goodbye.", voice="Polly.Joanna")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml")

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported telephony provider: {provider}",
    )
