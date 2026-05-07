"""
Integrations API — per-agent integration configuration.

Endpoints:
  GET    /api/integrations/{agent_id}                   — get agent integration config
  PUT    /api/integrations/{agent_id}                   — save/update integration config
  POST   /api/integrations/{agent_id}/test/{type}       — test a specific integration
  DELETE /api/integrations/{agent_id}/{type}            — remove an integration type key
  GET    /api/integrations/{agent_id}/variables         — list post_call_actions + last extraction
  POST   /api/integrations/{agent_id}/run-delivery/{call_log_id}  — re-run delivery for a past call
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Agent, CallLog, Tenant
from app.routes.auth import require_agent_access, AuthContext

logger = logging.getLogger("voiceflow.integrations")
router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class IntegrationConfig(BaseModel):
    """Arbitrary integration config dict — no fixed schema so we accept Any."""
    config: dict


class PostCallVariable(BaseModel):
    variable: str
    extraction_prompt: str
    data_type: str = "string"  # string | number | boolean | date | list


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_agent_checked(agent_id: str, auth: AuthContext, db: AsyncSession) -> Agent:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.tenantId != auth.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return agent


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{agent_id}")
async def get_integrations(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """Return the agent's per-agent integration config dict."""
    agent = await _get_agent_checked(agent_id, auth, db)
    return {"integrations": agent.integrations or {}}


@router.put("/{agent_id}")
async def save_integrations(
    agent_id: str,
    body: IntegrationConfig,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """
    Save/replace the agent's integration config.
    Secrets (passwords, API keys, tokens) should be passed as plaintext here;
    the backend stores them encrypted.
    """
    agent = await _get_agent_checked(agent_id, auth, db)

    # Encrypt sensitive fields before persisting
    config = body.config
    from app.services.credentials import encrypt_safe

    sensitive_paths = [
        ("hubspot", "accessToken"),
        ("salesforce", "password"),
        ("salesforce", "securityToken"),
        ("slack", "botToken"),
        ("email", "password"),
        ("email", "api_key"),
        ("gohighlevel", "apiKey"),
        ("calcom", "apiKey"),
    ]
    for section, key in sensitive_paths:
        val = config.get(section, {}).get(key)
        if val and not val.startswith("enc:"):
            config.setdefault(section, {})[key] = encrypt_safe(val)

    agent.integrations = config
    await db.commit()
    return {"status": "saved", "integrations": agent.integrations}


@router.post("/{agent_id}/test/{integration_type}")
async def test_integration(
    agent_id: str,
    integration_type: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """
    Smoke-test a specific integration using its stored config.
    Supported: hubspot | salesforce | slack | webhook | email | calcom | gcal | gohighlevel
    """
    agent = await _get_agent_checked(agent_id, auth, db)

    # Deep-merge tenant + agent configs
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    tenant_integrations: dict = (tenant.settings or {}).get("integrations", {}) if tenant else {}
    agent_integrations: dict = agent.integrations or {}
    merged: dict = {**tenant_integrations}
    for k, v in agent_integrations.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v

    cfg = merged.get(integration_type, {})
    if not cfg:
        raise HTTPException(status_code=400, detail=f"No config found for '{integration_type}'")

    from app.services.credentials import decrypt_safe

    def _d(v: str) -> str:
        return decrypt_safe(v) if v else ""

    ok = False
    detail = ""

    try:
        if integration_type == "hubspot":
            from hubspot import HubSpot  # type: ignore
            client = HubSpot(access_token=_d(cfg.get("accessToken", "")))
            import asyncio
            loop = asyncio.get_running_loop()
            me = await loop.run_in_executor(None, lambda: client.crm.contacts.basic_api.get_page(limit=1))
            ok = True
            detail = f"Connected — {(me.results[0].id if me.results else 'no contacts yet')}"

        elif integration_type == "salesforce":
            from simple_salesforce import Salesforce  # type: ignore
            import asyncio
            def _test():
                sf = Salesforce(
                    username=cfg.get("username", ""),
                    password=_d(cfg.get("password", "")),
                    security_token=_d(cfg.get("securityToken", "")),
                    instance_url=cfg.get("instanceUrl") or None,
                )
                return sf.query("SELECT Id FROM Lead LIMIT 1")
            await asyncio.get_running_loop().run_in_executor(None, _test)
            ok = True
            detail = "Salesforce connection successful"

        elif integration_type == "slack":
            from slack_sdk.web.async_client import AsyncWebClient  # type: ignore
            sc = AsyncWebClient(token=_d(cfg.get("botToken", "")))
            resp = await sc.auth_test()
            ok = True
            detail = f"Connected as {resp.get('user')} to {resp.get('team')}"

        elif integration_type == "email":
            provider = cfg.get("provider", "smtp")
            if provider == "sendgrid":
                import httpx
                async with httpx.AsyncClient(timeout=8) as client:
                    r = await client.get(
                        "https://api.sendgrid.com/v3/user/profile",
                        headers={"Authorization": f"Bearer {_d(cfg.get('api_key', ''))}"},
                    )
                ok = r.status_code == 200
                detail = f"SendGrid status: {r.status_code}"
            else:
                import smtplib, ssl as _ssl, asyncio
                def _test():
                    ctx = _ssl.create_default_context()
                    with smtplib.SMTP(cfg.get("host", "smtp.gmail.com"), int(cfg.get("port", 587))) as smtp:
                        smtp.ehlo()
                        smtp.starttls(context=ctx)
                        if cfg.get("username") and cfg.get("password"):
                            smtp.login(cfg["username"], _d(cfg["password"]))
                await asyncio.get_running_loop().run_in_executor(None, _test)
                ok = True
                detail = "SMTP connection successful"

        elif integration_type == "calcom":
            import httpx
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    "https://api.cal.com/v2/event-types",
                    headers={
                        "Authorization": f"Bearer {_d(cfg.get('apiKey', ''))}",
                        "cal-api-version": "2024-06-14",
                    },
                )
            ok = r.status_code == 200
            data = r.json() if ok else {}
            n = len((data.get("data", {}) or {}).get("eventTypeGroups") or data.get("event_types", []))
            detail = f"Cal.com connected — {n} event type groups"

        elif integration_type == "gcal":
            import asyncio, json as _json
            from app.services.voice_tools import voice_tool_executor
            result = await voice_tool_executor._execute_gcal(
                "check_gcal_availability",
                {"date": "2025-01-01"},
                {integration_type: cfg},
            )
            ok = "error" not in result
            detail = "Google Calendar connected" if ok else result.get("error", "failed")

        elif integration_type == "gohighlevel":
            import httpx
            location_id = cfg.get("locationId", "")
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(
                    "https://services.leadconnectorhq.com/contacts/",
                    headers={
                        "Authorization": f"Bearer {_d(cfg.get('apiKey', ''))}",
                        "Version": "2023-02-21",
                    },
                    params={"locationId": location_id, "limit": 1},
                )
            ok = r.status_code == 200
            detail = f"GHL connected (status: {r.status_code})" if ok else f"GHL status: {r.status_code}"

        elif integration_type == "webhook":
            import httpx, json as _json, hmac as _hmac, hashlib as _hs, time as _time
            test_payload = {"event": "test", "source": "voiceflow"}
            body = _json.dumps(test_payload).encode()
            secret = cfg.get("secret", "")
            sig = _hmac.new(secret.encode(), body, _hs.sha256).hexdigest() if secret else ""
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.post(
                    cfg.get("url", ""),
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-VoiceFlow-Signature": sig,
                        "X-VoiceFlow-Timestamp": str(int(_time.time())),
                    },
                )
            ok = r.status_code < 300
            detail = f"Webhook responded {r.status_code}"

        else:
            raise HTTPException(status_code=400, detail=f"Unknown integration type: {integration_type}")

    except HTTPException:
        raise
    except Exception as exc:
        ok = False
        detail = str(exc)

    return {"ok": ok, "detail": detail, "integration": integration_type}


@router.delete("/{agent_id}/{integration_type}")
async def remove_integration(
    agent_id: str,
    integration_type: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """Remove a specific integration key from the agent's config."""
    agent = await _get_agent_checked(agent_id, auth, db)
    integrations = dict(agent.integrations or {})
    integrations.pop(integration_type, None)
    agent.integrations = integrations
    await db.commit()
    return {"status": "removed", "integration": integration_type}


@router.get("/{agent_id}/variables")
async def get_variables(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """
    List post_call_actions (extracted variable configs) for the agent,
    plus the most recent extraction results from the last call.
    """
    agent = await _get_agent_checked(agent_id, auth, db)
    post_call_actions = (agent.llmPreferences or {}).get("post_call_actions", [])

    # Fetch the most recent CallLog that has extractedVariables
    res = await db.execute(
        select(CallLog)
        .where(CallLog.agentId == agent_id, CallLog.extractedVariables.isnot(None))
        .order_by(CallLog.createdAt.desc())
        .limit(1)
    )
    last_log = res.scalar_one_or_none()
    last_extraction = last_log.extractedVariables if last_log else {}

    return {
        "post_call_actions": post_call_actions,
        "last_extraction": last_extraction,
        "last_call_id": last_log.id if last_log else None,
    }


@router.put("/{agent_id}/variables")
async def save_variables(
    agent_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """
    Save the post_call_actions array on the agent's llmPreferences.
    Body: {"post_call_actions": [{"variable": "...", "extraction_prompt": "...", "data_type": "..."}]}
    """
    agent = await _get_agent_checked(agent_id, auth, db)
    prefs = dict(agent.llmPreferences or {})
    prefs["post_call_actions"] = body.get("post_call_actions", [])
    agent.llmPreferences = prefs
    await db.commit()
    return {"status": "saved", "post_call_actions": prefs["post_call_actions"]}


@router.post("/{agent_id}/run-delivery/{call_log_id}")
async def run_delivery(
    agent_id: str,
    call_log_id: str,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_agent_access),
):
    """
    Re-run post-call delivery (CRM push, Slack, webhooks, email) for a specific
    historical call. Useful for retrying failed deliveries or testing.
    """
    agent = await _get_agent_checked(agent_id, auth, db)

    log_res = await db.execute(
        select(CallLog).where(CallLog.id == call_log_id, CallLog.agentId == agent_id)
    )
    log = log_res.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="CallLog not found")

    import asyncio
    from app.routes.voice_twilio_gather import _run_post_call_delivery

    asyncio.create_task(
        _run_post_call_delivery(
            tenant_id=auth.tenant_id,
            agent_id=agent_id,
            call_log_id=call_log_id,
            transcript=log.transcript or "",
            analysis=log.analysis or {},
            groq_key=None,
            caller_phone=log.callerPhone or "",
            call_duration=log.durationSeconds or 0,
            call_sid=log.callSid or "",
            recording_url=log.recordingUrl or "",
        )
    )

    return {"status": "queued", "call_log_id": call_log_id}
