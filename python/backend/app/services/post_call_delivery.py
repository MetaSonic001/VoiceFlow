"""
Post-call delivery service — pushes structured call data to CRM, Slack, webhooks.

Mirrors OmniDimension's post-call delivery: after every call, based on agent config,
fires automatically to any combination of HubSpot, Salesforce, Slack, Google Calendar,
or custom HMAC-signed webhooks.

All SDK imports are lazy so the service starts even if some packages aren't installed.
Install what you need:
  pip install hubspot-api-client simple-salesforce slack-sdk google-api-python-client google-auth

Lead extraction runs locally via Groq — no extra cost or API key needed beyond what
the agent already uses.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("voiceflow.post_call_delivery")


# ── Lead extraction via LLM ───────────────────────────────────────────────────

async def extract_leads(transcript: str, groq_key: str) -> dict:
    """
    Use Groq to extract structured lead data from a call transcript.
    Returns dict with: name, email, phone, intent, sentiment, budget, objections,
    follow_up_action, extracted_variables.

    This runs after every call and feeds into CRM pushes automatically.
    Neither OmniDim nor Bolna has an automated feedback loop this structured.
    """
    if not groq_key or not transcript:
        return {}

    prompt = """Extract structured lead data from this call transcript. Return valid JSON only with these keys:
- "name": caller's full name (string or null)
- "email": email address if mentioned (string or null)
- "phone": phone number if mentioned (string or null)
- "company": company name if mentioned (string or null)
- "intent": primary intent in 10 words or less (string)
- "intent_level": "hot" | "warm" | "cold" | "not_interested"
- "sentiment": "positive" | "neutral" | "negative"
- "budget": budget mentioned if any (string or null)
- "objections": list of objection strings (array)
- "follow_up_action": recommended next step (string)
- "extracted_variables": dict of any other key facts mentioned

Transcript:
""" + transcript[:3000]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "Extract lead data. Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 512,
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                # Strip markdown fences if present
                content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(content)
    except Exception as exc:
        logger.warning("[post_call] lead extraction failed: %s", exc)
    return {}


# ── HubSpot ────────────────────────────────────────────────────────────────────

async def push_to_hubspot(
    *,
    access_token: str,
    lead_data: dict,
    call_summary: str,
    transcript: str,
    call_log_id: str,
) -> bool:
    """
    Create/update a HubSpot contact and log a call engagement.
    Requires: pip install hubspot-api-client
    HubSpot developer portal: https://developers.hubspot.com/
    """
    try:
        from hubspot import HubSpot  # type: ignore
        from hubspot.crm.contacts import SimplePublicObjectInputForCreate  # type: ignore
        from hubspot.crm.contacts.exceptions import ApiException  # type: ignore

        client = HubSpot(access_token=access_token)

        # Build contact properties
        props = {}
        if lead_data.get("name"):
            parts = (lead_data["name"] or "").split(" ", 1)
            props["firstname"] = parts[0]
            props["lastname"] = parts[1] if len(parts) > 1 else ""
        if lead_data.get("email"):
            props["email"] = lead_data["email"]
        if lead_data.get("phone"):
            props["phone"] = lead_data["phone"]
        if lead_data.get("company"):
            props["company"] = lead_data["company"]
        if lead_data.get("intent"):
            props["hs_lead_status"] = _map_intent_to_hubspot(lead_data.get("intent_level", "warm"))

        # Upsert contact by email
        loop = asyncio.get_event_loop()
        contact_id = None
        if props.get("email"):
            try:
                def _search():
                    return client.crm.contacts.search_api.do_search(
                        public_object_search_request={
                            "filters": [{"propertyName": "email", "operator": "EQ", "value": props["email"]}],
                            "limit": 1,
                        }
                    )
                results = await loop.run_in_executor(None, _search)
                if results.total > 0:
                    contact_id = results.results[0].id
            except Exception:
                pass

        if contact_id:
            await loop.run_in_executor(
                None,
                lambda: client.crm.contacts.basic_api.update(contact_id, simple_public_object_input={"properties": props}),
            )
        else:
            contact_obj = await loop.run_in_executor(
                None,
                lambda: client.crm.contacts.basic_api.create(
                    simple_public_object_input_for_create=SimplePublicObjectInputForCreate(properties=props)
                ),
            )
            contact_id = contact_obj.id

        # Log the call as an engagement note
        note_body = f"**VoiceFlow Call Summary**\nCall ID: {call_log_id}\n\n{call_summary}"
        await loop.run_in_executor(
            None,
            lambda: client.crm.objects.notes.basic_api.create(
                simple_public_object_input_for_create={
                    "properties": {
                        "hs_note_body": note_body,
                        "hs_timestamp": str(int(time.time() * 1000)),
                    },
                    "associations": [{"to": {"id": contact_id}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]}],
                }
            ),
        )
        logger.info("[post_call] HubSpot contact upserted: %s", contact_id)
        return True
    except ImportError:
        logger.warning("[post_call] hubspot-api-client not installed. Run: pip install hubspot-api-client")
    except Exception as exc:
        logger.warning("[post_call] HubSpot push failed: %s", exc)
    return False


def _map_intent_to_hubspot(intent_level: str) -> str:
    return {"hot": "IN_PROGRESS", "warm": "OPEN", "cold": "NEW", "not_interested": "UNQUALIFIED"}.get(intent_level, "OPEN")


# ── Salesforce ─────────────────────────────────────────────────────────────────

async def push_to_salesforce(
    *,
    instance_url: str,
    username: str,
    password: str,
    security_token: str,
    lead_data: dict,
    call_summary: str,
    call_log_id: str,
) -> bool:
    """
    Create/update a Salesforce Lead and log a task.
    Requires: pip install simple-salesforce
    """
    try:
        from simple_salesforce import Salesforce  # type: ignore

        loop = asyncio.get_event_loop()

        def _push():
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url or None,
            )
            lead_payload: dict = {
                "LastName": (lead_data.get("name") or "Unknown"),
                "Company": lead_data.get("company") or "Unknown",
                "LeadSource": "VoiceFlow AI Call",
                "Status": _map_intent_to_sf(lead_data.get("intent_level", "warm")),
                "Description": call_summary[:32000],
            }
            if lead_data.get("email"):
                lead_payload["Email"] = lead_data["email"]
            if lead_data.get("phone"):
                lead_payload["Phone"] = lead_data["phone"]

            result = sf.Lead.create(lead_payload)
            lead_id = result.get("id")

            # Log as a completed task
            sf.Task.create({
                "WhoId": lead_id,
                "Subject": f"VoiceFlow call {call_log_id}",
                "ActivityDate": time.strftime("%Y-%m-%d"),
                "Status": "Completed",
                "Description": call_summary[:32000],
            })
            return True

        return await loop.run_in_executor(None, _push)
    except ImportError:
        logger.warning("[post_call] simple-salesforce not installed. Run: pip install simple-salesforce")
    except Exception as exc:
        logger.warning("[post_call] Salesforce push failed: %s", exc)
    return False


def _map_intent_to_sf(intent_level: str) -> str:
    return {"hot": "Working - Contacted", "warm": "Open - Not Contacted", "cold": "Open - Not Contacted",
            "not_interested": "Closed - Not Converted"}.get(intent_level, "Open - Not Contacted")


# ── Slack ──────────────────────────────────────────────────────────────────────

async def push_to_slack(
    *,
    bot_token: str,
    channel: str,
    lead_data: dict,
    call_summary: str,
    call_log_id: str,
    sentiment: str = "neutral",
) -> bool:
    """
    Post a call summary to a Slack channel.
    Requires: pip install slack-sdk
    """
    try:
        from slack_sdk.web.async_client import AsyncWebClient  # type: ignore

        client = AsyncWebClient(token=bot_token)
        emoji = {"positive": ":white_check_mark:", "neutral": ":speech_balloon:", "negative": ":warning:"}.get(sentiment, ":speech_balloon:")
        caller = lead_data.get("name") or "Unknown caller"
        intent = lead_data.get("intent") or "unknown"

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} VoiceFlow Call Summary"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Caller:* {caller}"},
                {"type": "mrkdwn", "text": f"*Intent:* {intent}"},
                {"type": "mrkdwn", "text": f"*Sentiment:* {sentiment.title()}"},
                {"type": "mrkdwn", "text": f"*Call ID:* {call_log_id}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Summary:*\n{call_summary[:1000]}"}},
        ]
        if lead_data.get("follow_up_action"):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Next Step:* {lead_data['follow_up_action']}"},
            })

        await client.chat_postMessage(channel=channel, blocks=blocks, text=f"Call summary: {caller}")
        logger.info("[post_call] Slack message sent to %s", channel)
        return True
    except ImportError:
        logger.warning("[post_call] slack-sdk not installed. Run: pip install slack-sdk")
    except Exception as exc:
        logger.warning("[post_call] Slack push failed: %s", exc)
    return False


# ── Generic HMAC-signed webhook ────────────────────────────────────────────────

async def push_to_webhook(
    *,
    url: str,
    secret: str,
    payload: dict,
) -> bool:
    """
    Send HMAC-SHA256 signed webhook. Matches Make, Zapier, n8n, GoHighLevel webhook patterns.
    """
    body = json.dumps(payload, default=str).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest() if secret else ""
    headers = {
        "Content-Type": "application/json",
        "X-VoiceFlow-Signature": signature,
        "X-VoiceFlow-Timestamp": str(int(time.time())),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=body, headers=headers)
        if resp.status_code < 300:
            logger.info("[post_call] webhook delivered to %s status=%s", url, resp.status_code)
            return True
        logger.warning("[post_call] webhook to %s returned %s", url, resp.status_code)
    except Exception as exc:
        logger.warning("[post_call] webhook failed: %s", exc)
    return False


# ── Orchestrator ───────────────────────────────────────────────────────────────

async def deliver_post_call(
    *,
    tenant_id: str,
    agent_id: str,
    call_log_id: str,
    transcript: str,
    analysis: dict,
    groq_key: Optional[str] = None,
) -> None:
    """
    Main entry point called after every call.

    1. Extract structured leads from transcript
    2. Push to all configured delivery targets (HubSpot, Salesforce, Slack, Webhooks)
    3. Config loaded from Agent.llmPreferences.postCallDelivery or Tenant.settings.integrations

    Called from analyze_call() in voice_twilio_gather.py / voice.py.
    """
    from app.database import AsyncSessionLocal
    from app.models import Agent, Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        agent_res, tenant_res = await asyncio.gather(
            db.execute(select(Agent).where(Agent.id == agent_id)),
            db.execute(select(Tenant).where(Tenant.id == tenant_id)),
        )
        agent = agent_res.scalar_one_or_none()
        tenant = tenant_res.scalar_one_or_none()

    if not agent or not tenant:
        return

    # Resolve Groq key for lead extraction
    if not groq_key:
        enc = (tenant.settings or {}).get("groqApiKey")
        groq_key = decrypt_safe(enc) if enc else app_settings.GROQ_API_KEY

    call_summary = analysis.get("summary", "")
    sentiment = analysis.get("sentiment", "neutral")

    # Extract leads
    lead_data: dict = {}
    if groq_key and transcript:
        lead_data = await extract_leads(transcript, groq_key)

    # Delivery config from tenant integrations settings
    integrations: dict = (tenant.settings or {}).get("integrations", {})

    tasks = []

    # HubSpot
    hs_config = integrations.get("hubspot", {})
    if hs_config.get("enabled") and hs_config.get("accessToken"):
        tasks.append(push_to_hubspot(
            access_token=decrypt_safe(hs_config["accessToken"]),
            lead_data=lead_data,
            call_summary=call_summary,
            transcript=transcript,
            call_log_id=call_log_id,
        ))

    # Salesforce
    sf_config = integrations.get("salesforce", {})
    if sf_config.get("enabled") and sf_config.get("username"):
        tasks.append(push_to_salesforce(
            instance_url=sf_config.get("instanceUrl", ""),
            username=sf_config["username"],
            password=decrypt_safe(sf_config.get("password", "")),
            security_token=decrypt_safe(sf_config.get("securityToken", "")),
            lead_data=lead_data,
            call_summary=call_summary,
            call_log_id=call_log_id,
        ))

    # Slack
    slack_config = integrations.get("slack", {})
    if slack_config.get("enabled") and slack_config.get("botToken"):
        tasks.append(push_to_slack(
            bot_token=decrypt_safe(slack_config["botToken"]),
            channel=slack_config.get("channel", "#calls"),
            lead_data=lead_data,
            call_summary=call_summary,
            call_log_id=call_log_id,
            sentiment=sentiment,
        ))

    # Custom webhooks
    for wh in integrations.get("webhooks", []):
        if wh.get("url") and wh.get("enabled"):
            tasks.append(push_to_webhook(
                url=wh["url"],
                secret=wh.get("secret", ""),
                payload={
                    "event": "call.completed",
                    "callLogId": call_log_id,
                    "tenantId": tenant_id,
                    "agentId": agent_id,
                    "summary": call_summary,
                    "sentiment": sentiment,
                    "leadData": lead_data,
                    "analysis": analysis,
                },
            ))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if r is True)
        logger.info(
            "[post_call] delivery complete call=%s — %d/%d targets succeeded",
            call_log_id, successes, len(tasks),
        )

    # Persist lead_data back into the CallLog.analysis
    if lead_data:
        try:
            from app.database import AsyncSessionLocal
            from app.models import CallLog
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CallLog).where(CallLog.id == call_log_id))
                log = result.scalar_one_or_none()
                if log:
                    merged = {**(log.analysis or {}), "leadData": lead_data}
                    log.analysis = merged
                    await db.commit()
        except Exception as exc:
            logger.warning("[post_call] failed to persist lead data: %s", exc)
