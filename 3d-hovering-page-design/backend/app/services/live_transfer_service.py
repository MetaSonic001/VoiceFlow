"""
Live Transfer (Human-in-the-Loop) Service.

When the AI agent detects it cannot resolve a caller's request, it seamlessly
transfers the call to a human agent with full context handoff.

Transfer flow:
  1. Detect escalation intent in the caller's last utterance (keyword + LLM check)
  2. Agent says: "Let me connect you with a specialist who can help."
  3. Play hold music (configurable URL) while the handoff webhook fires
  4. Fire a webhook to the human agent platform (Freshdesk, Zendesk, or custom)
     with: caller phone, live transcript so far, extracted lead data, agent context
  5. Redirect Twilio call to the human agent's SIP or Twilio number via <Dial>
  6. Human agent receives the call AND the context pop-up (via webhook payload)

This solves the #1 enterprise objection: "What if the AI can't handle it?"
Neither OmniDimension nor Bolna does the context handoff cleanly.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger("voiceflow.live_transfer")

# ── Escalation detection ──────────────────────────────────────────────────────

_ESCALATION_KEYWORDS = re.compile(
    r"\b(speak.*(human|person|agent|manager|supervisor|representative|rep)"
    r"|transfer me|connect me|real person|talk to someone|human help"
    r"|this is (urgent|emergency)|need a manager|not helpful|frustrated|stupid bot"
    r"|doesn't understand|can't help|useless|human please)\b",
    re.IGNORECASE,
)


def detect_escalation_intent(utterance: str) -> bool:
    """
    Fast keyword-based escalation detection.
    Returns True if the caller is likely requesting human escalation.
    Use this as a first pass before the LLM check to save latency.
    """
    return bool(_ESCALATION_KEYWORDS.search(utterance or ""))


async def llm_escalation_check(utterance: str, groq_api_key: str) -> bool:
    """
    LLM-based escalation detection for ambiguous cases.
    Only called when keyword detection is inconclusive.
    Uses Groq llama-3.1-8b-instant for low latency (~200ms).
    """
    if not groq_api_key or not utterance:
        return False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_api_key}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a call routing classifier. Answer only 'yes' or 'no'. "
                                "Does the following utterance indicate the caller wants to speak "
                                "to a human agent or be transferred?"
                            ),
                        },
                        {"role": "user", "content": utterance[:500]},
                    ],
                    "max_tokens": 5,
                    "temperature": 0.0,
                },
            )
            if resp.status_code == 200:
                answer = resp.json()["choices"][0]["message"]["content"].strip().lower()
                return answer.startswith("yes")
    except Exception as exc:
        logger.debug("[live_transfer] LLM escalation check failed: %s", exc)
    return False


# ── Context handoff payload ───────────────────────────────────────────────────

def build_handoff_payload(
    caller_phone: str,
    transcript: str,
    agent_name: str,
    lead_data: Optional[dict] = None,
    crm_context: Optional[dict] = None,
    call_log_id: Optional[str] = None,
) -> dict:
    """
    Build the handoff payload sent to the human agent platform.
    This is the "context pop" that appears on screen when the human answers.
    """
    return {
        "event": "live_transfer",
        "call_log_id": call_log_id,
        "caller_phone": caller_phone,
        "ai_agent": agent_name,
        "transcript_so_far": transcript[-3000:] if transcript else "",  # last 3000 chars
        "caller_name": (lead_data or {}).get("name"),
        "caller_intent": (lead_data or {}).get("intent"),
        "caller_sentiment": (lead_data or {}).get("sentiment"),
        "crm_context": crm_context or {},
        "lead_data": lead_data or {},
        "summary": (
            f"Caller {(lead_data or {}).get('name', caller_phone)} "
            f"was transferred from AI agent '{agent_name}'. "
            f"Intent: {(lead_data or {}).get('intent', 'unknown')}."
        ),
    }


async def fire_handoff_webhook(
    webhook_url: str,
    payload: dict,
    secret: Optional[str] = None,
) -> bool:
    """
    Fire the context handoff webhook to a human agent platform.
    Optionally signed with HMAC-SHA256 (same pattern as post-call webhooks).
    """
    import hashlib
    import hmac
    import json

    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload).encode()

    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-VoiceFlow-Signature"] = f"sha256={sig}"

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(webhook_url, content=body, headers=headers)
            if resp.status_code < 300:
                logger.info("[live_transfer] handoff webhook fired: %s", webhook_url)
                return True
            logger.warning("[live_transfer] handoff webhook %s returned %s", webhook_url, resp.status_code)
    except Exception as exc:
        logger.warning("[live_transfer] handoff webhook error: %s", exc)
    return False


def build_transfer_twiml(
    human_number: str,
    hold_music_url: Optional[str] = None,
    caller_id: Optional[str] = None,
) -> str:
    """
    Build TwiML to transfer the call to a human agent.
    Plays hold music briefly before dialing.
    """
    hold_music = hold_music_url or "http://com.twilio.music.classical.s3.amazonaws.com/BusyStrings.mp3"
    caller_id_part = f' callerId="{caller_id}"' if caller_id else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play loop="1">{hold_music}</Play>
  <Dial{caller_id_part} timeout="30" record="do-not-record">
    <Number>{human_number}</Number>
  </Dial>
  <Say>We were unable to connect you to a specialist. Please call back.</Say>
</Response>"""


async def execute_transfer(
    call_sid: str,
    human_number: str,
    tenant_settings: dict,
    caller_phone: str,
    transcript: str,
    agent_name: str,
    lead_data: Optional[dict] = None,
    crm_context: Optional[dict] = None,
    call_log_id: Optional[str] = None,
    twilio_sid: Optional[str] = None,
    twilio_token: Optional[str] = None,
) -> bool:
    """
    Full transfer execution:
    1. Fire handoff webhook with context
    2. Update the live Twilio call with transfer TwiML

    Returns True if Twilio call update succeeded.
    """
    # 1. Fire handoff webhook first (parallel with Twilio call)
    handoff_payload = build_handoff_payload(
        caller_phone=caller_phone,
        transcript=transcript,
        agent_name=agent_name,
        lead_data=lead_data,
        crm_context=crm_context,
        call_log_id=call_log_id,
    )

    transfer_cfg: dict = tenant_settings.get("liveTransfer", {})
    webhook_url = transfer_cfg.get("webhookUrl")
    webhook_secret = transfer_cfg.get("webhookSecret")

    import asyncio
    tasks = []
    if webhook_url:
        tasks.append(fire_handoff_webhook(webhook_url, handoff_payload, webhook_secret))

    # 2. Build and push transfer TwiML to Twilio
    hold_music = transfer_cfg.get("holdMusicUrl")
    twiml = build_transfer_twiml(human_number, hold_music)

    sid = twilio_sid
    token = twilio_token
    if not sid or not token:
        from app.config import settings
        sid, token = settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN

    async def _push_twiml():
        if not sid or not token:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls/{call_sid}.json",
                    auth=(sid, token),
                    data={"Twiml": twiml},
                )
                return resp.status_code in (200, 204)
        except Exception as exc:
            logger.warning("[live_transfer] Twilio call update failed: %s", exc)
            return False

    tasks.append(_push_twiml())
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return any(r is True for r in results)
