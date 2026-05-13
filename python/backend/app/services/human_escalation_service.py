"""
Human escalation orchestration: live transfer, callback logging, tickets, and notify webhooks.

Integrates with:
  - live_transfer_service.execute_transfer (Twilio PSTN)
  - tenant.settings.humanEscalation — ticket / notify URLs
  - Agent.llmPreferences — default handoff number, auto-transfer toggles
  - Workflow human_transfer nodes — per-scenario destination numbers
"""
from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Tenant

logger = logging.getLogger("voiceflow.human_escalation")

# Set by voice routes around streaming RAG so transfer_call tool can reach Twilio context.
voice_escalation_ctx: ContextVar[dict[str, Any] | None] = ContextVar(
    "voice_escalation_ctx", default=None
)

_CALLBACK_RE = re.compile(
    r"(?i)\b(call\s*me\s*back|callback|schedule\s*a\s*call|phone\s*me\s*(later|tomorrow)?"
    r"|ring\s*me|contact\s*me\s*(later|tomorrow)?)\b",
)


def schedule_callback_requested(user_message: str) -> bool:
    return bool(_CALLBACK_RE.search(user_message or ""))


def workflow_transfer_number(flow_definition: dict | None, node_id: str | None) -> Optional[str]:
    """Return E.164 or raw destination from a human_transfer node."""
    if not flow_definition or not node_id:
        return None
    nodes = {n["id"]: n for n in flow_definition.get("nodes") or [] if n.get("id")}
    node = nodes.get(node_id)
    if not node or node.get("type") != "human_transfer":
        return None
    num = (node.get("number") or node.get("transferTo") or "").strip()
    return num or None


def _merge_tenant_agent_prefs(agent: Agent | None, tenant: Tenant | None) -> dict[str, Any]:
    prefs: dict[str, Any] = {}
    if agent and agent.llmPreferences:
        prefs.update(agent.llmPreferences)
    return prefs


def resolve_handoff_number(
    *,
    agent: Agent | None,
    tenant: Tenant | None,
    override_number: Optional[str] = None,
) -> Optional[str]:
    """Pick destination for warm transfer (workflow override wins)."""
    if override_number and override_number.strip():
        return override_number.strip()

    prefs = _merge_tenant_agent_prefs(agent, tenant)
    for key in ("humanHandoffNumber", "defaultHumanNumber", "transferNumber"):
        v = prefs.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    ts = (tenant.settings or {}) if tenant else {}
    lt = ts.get("liveTransfer") or {}
    for key in ("queueNumber", "defaultNumber", "transferTo"):
        v = lt.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return None


async def _emit_json_webhook(url: str, payload: dict, secret: Optional[str]) -> bool:
    import hashlib
    import hmac

    import httpx

    body = json.dumps(payload, default=str).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-VoiceFlow-Signature"] = f"sha256={sig}"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.post(url, content=body, headers=headers)
            return resp.status_code < 300
    except Exception as exc:
        logger.warning("[human_escalation] webhook POST failed %s: %s", url[:80], exc)
        return False


async def emit_escalation_payloads(
    tenant: Tenant | None,
    *,
    event_type: str,
    payload: dict,
) -> None:
    """
    Fan-out to ticket + notify URLs from tenant.settings.humanEscalation.

    Example tenant.settings.humanEscalation:
      {
        "ticketWebhookUrl": "https://hooks.zapier.com/...",
        "notifyWebhookUrl": "https://slack.com/api/...",
        "sharedSecret": "optional-signing-key"
      }
    """
    if not tenant or not tenant.settings:
        return
    he = tenant.settings.get("humanEscalation") or {}
    if isinstance(he, str):
        return
    secret = he.get("sharedSecret") or he.get("webhookSecret")
    full = {
        "event": event_type,
        "tenantId": tenant.id,
        "tenantName": tenant.name,
        **payload,
    }
    for key in ("ticketWebhookUrl", "notifyWebhookUrl"):
        url = he.get(key)
        if isinstance(url, str) and url.startswith("http"):
            await _emit_json_webhook(url, full, secret)


async def maybe_transfer_twilio_call(
    *,
    call_sid: str,
    transfer_to: str,
    tenant: Tenant | None,
    caller_phone: str,
    transcript_snippet: str,
    agent_name: str,
    provider: str,
) -> bool:
    """Run PSTN transfer once per call (Twilio only)."""
    if provider != "twilio":
        logger.info("[human_escalation] PSTN transfer skipped for provider=%s", provider)
        return False
    if not tenant:
        return False

    from app.services.live_transfer_service import execute_transfer
    from app.services.rag_service import get_redis

    r = await get_redis()
    if r:
        try:
            dk = f"transfer_done:{call_sid}"
            ok = await r.set(dk, b"1", nx=True, ex=7200)
            if not ok:
                logger.info("[human_escalation] transfer already executed call=%s", call_sid)
                return False
        except Exception:
            pass

    ts = tenant.settings or {}
    ok = await execute_transfer(
        call_sid=call_sid,
        human_number=transfer_to,
        tenant_settings=ts,
        caller_phone=caller_phone or "unknown",
        transcript=transcript_snippet or "",
        agent_name=agent_name,
        lead_data=None,
        crm_context=None,
        call_log_id=None,
        twilio_sid=None,
        twilio_token=None,
    )
    if ok:
        logger.info("[human_escalation] warm transfer initiated call=%s → %s", call_sid, transfer_to)
    return ok


async def record_callback_request_redis(
    tenant_id: str,
    agent_id: str,
    call_sid: str,
    *,
    caller_phone: str,
    user_message: str,
) -> None:
    from app.services.rag_service import get_redis

    r = await get_redis()
    if not r:
        return
    key = f"callback_request:{tenant_id}:{call_sid}"
    try:
        await r.set(
            key,
            json.dumps(
                {
                    "caller_phone": caller_phone,
                    "user_message": user_message[:2000],
                    "agent_id": agent_id,
                },
                default=str,
            ),
            ex=86400 * 7,
        )
    except Exception:
        logger.exception("[human_escalation] redis callback record failed")


async def post_voice_turn_escalation(
    *,
    db: AsyncSession,
    tenant_id: str,
    agent_id: str,
    session_id: str,
    user_message: str,
    assistant_message: str,
    flow_definition: dict | None,
    workflow_response_node_id: Optional[str],
    voice_context: dict[str, Any] | None,
) -> None:
    """
    After a voice turn completes: workflow transfer, keyword escalation, callback intent,
    and webhook fan-out. Twilio-only for actual PSTN redirect.
    """
    if not voice_context:
        return
    prov = (voice_context.get("provider") or "twilio").lower()
    if prov not in ("twilio", "exotel"):
        return

    call_sid = voice_context.get("call_sid") or ""
    if not call_sid:
        return

    result_t = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    result_a = await db.execute(select(Agent).where(Agent.id == agent_id))
    tenant = result_t.scalar_one_or_none()
    agent = result_a.scalar_one_or_none()

    caller_phone = str(voice_context.get("caller_phone") or "")
    agent_name = (agent.name if agent else "") or "Assistant"

    wf_number = workflow_transfer_number(flow_definition, workflow_response_node_id)
    default_number = resolve_handoff_number(agent=agent, tenant=tenant, override_number=None)

    from app.services.live_transfer_service import detect_escalation_intent

    prefs = _merge_tenant_agent_prefs(agent, tenant)
    auto_xfer = prefs.get("autoTransferOnEscalation", True)
    keyword_hit = detect_escalation_intent(user_message)

    target: Optional[str] = wf_number
    if target is None and keyword_hit and auto_xfer:
        target = default_number

    transcript_snippet = f"User: {user_message}\nAssistant: {assistant_message}"[-4000:]

    base_payload = {
        "session_id": session_id,
        "call_sid": call_sid,
        "caller_phone": caller_phone,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "user_message": user_message[:4000],
        "assistant_message": assistant_message[:4000],
        "workflow_node_id": workflow_response_node_id,
        "transfer_target": target,
    }

    # Tickets / notify for every qualifying escalation signal
    if tenant and (wf_number or keyword_hit or schedule_callback_requested(user_message)):
        evt = "human_escalation"
        if schedule_callback_requested(user_message):
            evt = "callback_requested"
            await record_callback_request_redis(tenant_id, agent_id, call_sid, caller_phone=caller_phone, user_message=user_message)
        await emit_escalation_payloads(tenant, event_type=evt, payload=base_payload)

    # PSTN transfer (Twilio)
    if target and prov == "twilio":
        await maybe_transfer_twilio_call(
            call_sid=call_sid,
            transfer_to=target,
            tenant=tenant,
            caller_phone=caller_phone,
            transcript_snippet=transcript_snippet,
            agent_name=agent_name,
            provider=prov,
        )
    elif target and prov == "exotel":
        await emit_escalation_payloads(
            tenant,
            event_type="transfer_requested_exotel",
            payload={
                **base_payload,
                "note": "Configure Exotel outbound bridge or agent dashboard for PSTN handoff; webhook carries context.",
            },
        )
