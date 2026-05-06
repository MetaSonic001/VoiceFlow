"""
Post-call delivery service — complete pipeline firing after every call.

Pipeline:
  1. Extract structured variables via post_call_actions config (per-agent LLM extraction)
  2. Generate call summary via LLM
  3. Deliver in parallel to all configured destinations:
     Email (SMTP/SendGrid), HubSpot, Salesforce, Slack (Block Kit),
     HMAC-signed webhooks (Make/Zapier/n8n compatible), GoHighLevel

Design:
- All destinations are fire-and-forget with structured error logging
- Credentials encrypted at rest, decrypted only at delivery time
- Fail-open: one delivery failure never blocks others
- Per-agent integrations override tenant-level defaults

Install optional SDKs:
  pip install hubspot-api-client simple-salesforce slack-sdk sendgrid
"""
from __future__ import annotations

import asyncio
import email.mime.multipart
import email.mime.text
import hashlib
import hmac
import json
import logging
import smtplib
import ssl
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("voiceflow.post_call_delivery")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. STRUCTURED VARIABLE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

async def extract_variables(
    transcript: str,
    post_call_actions: list[dict],
    groq_key: str,
) -> dict:
    """
    Run a single batch LLM call to extract all agent-configured variables.

    Each post_call_actions entry:
        {"variable": "patient_name", "extraction_prompt": "...", "data_type": "string"}
    Supported data_type: string | number | boolean | date | list

    Returns {"patient_name": "John Smith", "appointment_date": "2025-06-10", ...}
    Variables not found in transcript → null.
    """
    if not post_call_actions or not transcript or not groq_key:
        return {}

    var_lines = []
    for a in post_call_actions:
        var = a.get("variable", "")
        prompt_text = a.get("extraction_prompt", f"Extract {var}")
        dtype = a.get("data_type", "string")
        var_lines.append(f'- "{var}" ({dtype}): {prompt_text}')

    system_prompt = (
        "You are a data extraction assistant. Extract all requested variables "
        "from the transcript. Return valid JSON only — no markdown, no explanation. "
        "Use null for any variable not mentioned."
    )
    user_prompt = (
        "Extract these variables from the transcript below:\n"
        + "\n".join(var_lines)
        + f"\n\nTranscript:\n{transcript[:4000]}"
        + "\n\nReturn a JSON object with exactly these keys: "
        + ", ".join(f'"{a.get("variable", "")}"' for a in post_call_actions)
    )

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 512,
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                result = json.loads(content)
                # Coerce types
                for a in post_call_actions:
                    var = a.get("variable", "")
                    dtype = a.get("data_type", "string")
                    val = result.get(var)
                    if val is not None:
                        try:
                            if dtype == "number":
                                result[var] = float(val) if "." in str(val) else int(val)
                            elif dtype == "boolean":
                                result[var] = str(val).lower() in ("true", "yes", "1")
                        except (ValueError, TypeError):
                            pass
                logger.info("[post_call] extracted %d variables", len(result))
                return result
    except Exception as exc:
        logger.warning("[post_call] variable extraction failed: %s", exc)
    return {}


async def extract_leads(transcript: str, groq_key: str) -> dict:
    """
    General lead extraction — fills standard CRM fields not covered by post_call_actions.
    Returns: name, email, phone, company, intent, intent_level, sentiment,
             sentiment_score, budget, objections, follow_up_action, call_outcome.
    """
    if not groq_key or not transcript:
        return {}

    prompt = (
        "Extract structured lead data from this call transcript. Return valid JSON only:\n"
        '- "name": caller full name (string or null)\n'
        '- "email": email address (string or null)\n'
        '- "phone": phone number (string or null)\n'
        '- "company": company name (string or null)\n'
        '- "intent": primary intent in 10 words or less\n'
        '- "intent_level": "hot" | "warm" | "cold" | "not_interested"\n'
        '- "sentiment": "positive" | "neutral" | "negative"\n'
        '- "sentiment_score": 0.0-1.0 float\n'
        '- "budget": budget mentioned (string or null)\n'
        '- "objections": array of objection strings\n'
        '- "follow_up_action": recommended next step\n'
        '- "call_outcome": "interested" | "not_interested" | "follow_up" | "booked" | "transferred"\n'
        f"\nTranscript:\n{transcript[:3000]}"
    )
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
                    "max_tokens": 600,
                    "response_format": {"type": "json_object"},
                },
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                return json.loads(content)
    except Exception as exc:
        logger.warning("[post_call] lead extraction failed: %s", exc)
    return {}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. EMAIL DELIVERY (SMTP + SENDGRID)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_email_html(
    agent_name: str,
    lead_data: dict,
    extracted_vars: dict,
    call_summary: str,
    duration: int,
    call_log_id: str,
    sentiment: str,
) -> tuple[str, str]:
    """Return (subject, html_body) for the post-call email report."""
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    subject = f"[VoiceFlow] Call Summary — {agent_name} — {date_str}"

    sentiment_color = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#6b7280"}.get(sentiment, "#6b7280")
    mins, secs = divmod(duration or 0, 60)
    duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"

    vars_rows = ""
    for k, v in {**(lead_data or {}), **(extracted_vars or {})}.items():
        if v is not None and k not in ("extracted_variables", "objections"):
            vars_rows += (
                f"<tr>"
                f"<td style='padding:6px 8px;border:1px solid #e5e7eb;font-size:13px;"
                f"color:#374151;font-weight:600'>{k.replace('_',' ').title()}</td>"
                f"<td style='padding:6px 8px;border:1px solid #e5e7eb;font-size:13px;color:#374151'>{v}</td>"
                f"</tr>"
            )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:sans-serif;background:#f9fafb;margin:0;padding:24px">
  <div style="max-width:620px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)">
    <div style="background:linear-gradient(135deg,#0d9488,#06b6d4);padding:24px 32px">
      <h1 style="color:#fff;margin:0;font-size:20px">VoiceFlow — Call Summary</h1>
      <p style="color:rgba(255,255,255,.8);margin:4px 0 0;font-size:13px">{date_str}</p>
    </div>
    <div style="padding:28px 32px">
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
        <tr><td style="padding:6px 0;color:#6b7280;font-size:13px;width:130px">Agent</td>
            <td style="padding:6px 0;color:#111827;font-size:13px;font-weight:600">{agent_name}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-size:13px">Duration</td>
            <td style="padding:6px 0;color:#111827;font-size:13px">{duration_str}</td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-size:13px">Sentiment</td>
            <td style="padding:6px 0;font-size:13px"><span style="color:{sentiment_color};font-weight:600">{sentiment.title()}</span></td></tr>
        <tr><td style="padding:6px 0;color:#6b7280;font-size:13px">Call ID</td>
            <td style="padding:6px 0;color:#6b7280;font-size:11px;font-family:monospace">{call_log_id}</td></tr>
      </table>

      <h2 style="color:#111827;font-size:15px;margin:0 0 8px">Summary</h2>
      <p style="color:#374151;font-size:14px;line-height:1.6;margin:0 0 24px;background:#f3f4f6;padding:14px;border-radius:8px">{call_summary or 'No summary available.'}</p>

      {"<h2 style='color:#111827;font-size:15px;margin:0 0 8px'>Extracted Data</h2><table style='width:100%;border-collapse:collapse;margin-bottom:24px'><tr><th style='padding:8px;background:#f3f4f6;border:1px solid #e5e7eb;font-size:12px;color:#6b7280;text-align:left'>Field</th><th style='padding:8px;background:#f3f4f6;border:1px solid #e5e7eb;font-size:12px;color:#6b7280;text-align:left'>Value</th></tr>" + vars_rows + "</table>" if vars_rows else ""}
    </div>
    <div style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb">
      <p style="color:#9ca3af;font-size:12px;margin:0">Sent by VoiceFlow AI Platform</p>
    </div>
  </div>
</body></html>"""
    return subject, html


async def push_to_email(
    *,
    email_config: dict,
    agent_name: str,
    lead_data: dict,
    extracted_vars: dict,
    call_summary: str,
    duration: int,
    call_log_id: str,
    sentiment: str,
) -> bool:
    """
    Send a formatted HTML post-call report to configured recipients.

    email_config keys:
      provider: "smtp" | "sendgrid"
      smtp: host, port, username, password, from_address
      sendgrid: api_key, from_address
      recipients: ["a@b.com", ...]
    """
    recipients = email_config.get("recipients", [])
    if not recipients:
        return False

    subject, html_body = _build_email_html(
        agent_name, lead_data, extracted_vars,
        call_summary, duration, call_log_id, sentiment,
    )
    text_body = f"{subject}\n\n{call_summary}\n\nCall ID: {call_log_id}"
    from_addr = email_config.get("from_address", "noreply@voiceflow.ai")
    provider = email_config.get("provider", "smtp")

    try:
        if provider == "sendgrid":
            api_key = email_config.get("api_key", "")
            if not api_key:
                return False
            try:
                from sendgrid import SendGridAPIClient  # type: ignore
                from sendgrid.helpers.mail import Mail  # type: ignore

                message = Mail(
                    from_email=from_addr,
                    to_emails=recipients,
                    subject=subject,
                    html_content=html_body,
                )
                message.plain_text_content = text_body
                sg = SendGridAPIClient(api_key)
                response = await asyncio.get_event_loop().run_in_executor(None, sg.send, message)
                if response.status_code in (200, 201, 202):
                    logger.info("[post_call] email sent via SendGrid to %d recipients", len(recipients))
                    return True
                logger.warning("[post_call] SendGrid returned %s", response.status_code)
                return False
            except ImportError:
                logger.warning("[post_call] sendgrid not installed. Run: pip install sendgrid")

        # SMTP
        host = email_config.get("host", "smtp.gmail.com")
        port = int(email_config.get("port", 587))
        username = email_config.get("username", "")
        password = email_config.get("password", "")

        def _send() -> None:
            msg = email.mime.multipart.MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = ", ".join(recipients)
            msg.attach(email.mime.text.MIMEText(text_body, "plain"))
            msg.attach(email.mime.text.MIMEText(html_body, "html"))
            ctx = ssl.create_default_context()
            with smtplib.SMTP(host, port) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ctx)
                if username and password:
                    smtp.login(username, password)
                smtp.sendmail(from_addr, recipients, msg.as_string())

        await asyncio.get_event_loop().run_in_executor(None, _send)
        logger.info("[post_call] email sent via SMTP to %d recipients", len(recipients))
        return True

    except Exception as exc:
        logger.warning("[post_call] email delivery failed: %s", exc)
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 3. HUBSPOT
# ═══════════════════════════════════════════════════════════════════════════════

async def push_to_hubspot(
    *,
    access_token: str,
    lead_data: dict,
    extracted_vars: dict,
    call_summary: str,
    transcript: str,
    call_log_id: str,
    caller_phone: str = "",
    duration: int = 0,
    field_map: Optional[dict] = None,
    create_deal: bool = False,
) -> bool:
    """
    Create/update a HubSpot Contact (phone-first lookup), log a note, optionally create a Deal.
    Requires: pip install hubspot-api-client
    field_map: {"extracted_var_key": "hubspot_property_name", ...}
    """
    try:
        from hubspot import HubSpot  # type: ignore
        from hubspot.crm.contacts import SimplePublicObjectInputForCreate  # type: ignore

        client = HubSpot(access_token=access_token)
        loop = asyncio.get_event_loop()

        props: dict = {}
        if lead_data.get("name"):
            parts = (lead_data["name"] or "").split(" ", 1)
            props["firstname"] = parts[0]
            props["lastname"] = parts[1] if len(parts) > 1 else ""
        if lead_data.get("email"):
            props["email"] = lead_data["email"]
        phone = caller_phone or lead_data.get("phone", "")
        if phone:
            props["phone"] = phone
        if lead_data.get("company"):
            props["company"] = lead_data["company"]
        if lead_data.get("intent_level"):
            props["hs_lead_status"] = _map_intent_to_hubspot(lead_data["intent_level"])

        # Apply field_map from extracted variables
        for ev_key, hs_prop in (field_map or {}).items():
            val = extracted_vars.get(ev_key)
            if val is not None:
                props[hs_prop] = str(val)

        contact_id: Optional[str] = None

        # Phone-first lookup, then email
        for search_field, search_val in [("phone", phone), ("email", lead_data.get("email", ""))]:
            if not search_val or contact_id:
                continue
            try:
                def _search(f=search_field, v=search_val):
                    return client.crm.contacts.search_api.do_search(
                        public_object_search_request={
                            "filters": [{"propertyName": f, "operator": "EQ", "value": v}],
                            "limit": 1,
                        }
                    )
                res = await loop.run_in_executor(None, _search)
                if res.total > 0:
                    contact_id = res.results[0].id
            except Exception:
                pass

        if contact_id:
            await loop.run_in_executor(
                None,
                lambda cid=contact_id: client.crm.contacts.basic_api.update(
                    cid, simple_public_object_input={"properties": props}
                ),
            )
        else:
            contact_obj = await loop.run_in_executor(
                None,
                lambda: client.crm.contacts.basic_api.create(
                    simple_public_object_input_for_create=SimplePublicObjectInputForCreate(properties=props)
                ),
            )
            contact_id = contact_obj.id

        # Build contextual note
        vars_section = ""
        if extracted_vars:
            vars_section = "\n\nExtracted Variables:\n" + "\n".join(
                f"  • {k}: {v}" for k, v in extracted_vars.items() if v is not None
            )
        duration_str = f"{duration // 60}m {duration % 60}s" if duration else "unknown"
        note_body = (
            f"VoiceFlow Call Summary\n"
            f"Call ID: {call_log_id} | Duration: {duration_str}\n\n"
            f"{call_summary}"
            f"{vars_section}"
        )
        await loop.run_in_executor(
            None,
            lambda cid=contact_id: client.crm.objects.notes.basic_api.create(
                simple_public_object_input_for_create={
                    "properties": {
                        "hs_note_body": note_body,
                        "hs_timestamp": str(int(time.time() * 1000)),
                    },
                    "associations": [{"to": {"id": cid}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]}],
                }
            ),
        )

        # Create Deal when caller outcome is 'interested'
        if create_deal and lead_data.get("call_outcome") == "interested":
            deal_name = f"VoiceFlow Lead — {lead_data.get('name') or phone}"
            await loop.run_in_executor(
                None,
                lambda cid=contact_id: client.crm.deals.basic_api.create(
                    simple_public_object_input_for_create={
                        "properties": {
                            "dealname": deal_name,
                            "pipeline": "default",
                            "dealstage": "appointmentscheduled",
                        },
                        "associations": [{"to": {"id": cid}, "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 4}]}],
                    }
                ),
            )
            logger.info("[post_call] HubSpot Deal created for contact %s", contact_id)

        logger.info("[post_call] HubSpot contact upserted: %s", contact_id)
        return True
    except ImportError:
        logger.warning("[post_call] hubspot-api-client not installed. Run: pip install hubspot-api-client")
    except Exception as exc:
        logger.warning("[post_call] HubSpot push failed: %s", exc)
    return False


def _map_intent_to_hubspot(intent_level: str) -> str:
    return {"hot": "IN_PROGRESS", "warm": "OPEN", "cold": "NEW", "not_interested": "UNQUALIFIED"}.get(intent_level, "OPEN")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SALESFORCE
# ═══════════════════════════════════════════════════════════════════════════════

async def push_to_salesforce(
    *,
    instance_url: str,
    username: str,
    password: str,
    security_token: str,
    lead_data: dict,
    extracted_vars: dict,
    call_summary: str,
    call_log_id: str,
    caller_phone: str = "",
    duration: int = 0,
    object_type: str = "Lead",
    field_map: Optional[dict] = None,
) -> bool:
    """
    Create/update a Salesforce Lead or Contact and log an Activity (Task).
    Requires: pip install simple-salesforce
    object_type: "Lead" | "Contact"
    field_map: {"extracted_var_key": "SalesforceField__c", ...}
    """
    try:
        from simple_salesforce import Salesforce  # type: ignore

        loop = asyncio.get_event_loop()

        def _push() -> bool:
            sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                instance_url=instance_url or None,
            )
            phone = caller_phone or lead_data.get("phone", "")
            payload: dict = {
                "LastName": (lead_data.get("name") or "Unknown"),
                "LeadSource": "VoiceFlow AI Call",
                "Description": call_summary[:32000],
            }
            if object_type == "Lead":
                payload["Company"] = lead_data.get("company") or "Unknown"
                payload["Status"] = _map_intent_to_sf(lead_data.get("intent_level", "warm"))
            if lead_data.get("email"):
                payload["Email"] = lead_data["email"]
            if phone:
                payload["Phone"] = phone

            # Apply field_map from extracted variables
            for ev_key, sf_field in (field_map or {}).items():
                val = extracted_vars.get(ev_key)
                if val is not None:
                    payload[sf_field] = str(val)

            # Try to find existing record by phone or email
            record_id: Optional[str] = None
            sf_obj = getattr(sf, object_type)
            for search_field, val in [("Phone", phone), ("Email", lead_data.get("email", ""))]:
                if not val or record_id:
                    continue
                try:
                    q = sf.query(
                        f"SELECT Id FROM {object_type} WHERE {search_field} = '{val}' LIMIT 1"
                    )
                    if q.get("totalSize", 0) > 0:
                        record_id = q["records"][0]["Id"]
                except Exception:
                    pass

            if record_id:
                sf_obj.update(record_id, payload)
            else:
                result = sf_obj.create(payload)
                record_id = result.get("id")

            # Log as a completed task
            duration_str = f"{duration // 60}m {duration % 60}s" if duration else "n/a"
            sf.Task.create({
                "WhoId": record_id,
                "Subject": f"VoiceFlow call {call_log_id}",
                "ActivityDate": time.strftime("%Y-%m-%d"),
                "Status": "Completed",
                "Description": f"Duration: {duration_str}\n\n{call_summary[:32000]}",
            })
            return True

        return await loop.run_in_executor(None, _push)
    except ImportError:
        logger.warning("[post_call] simple-salesforce not installed. Run: pip install simple-salesforce")
    except Exception as exc:
        logger.warning("[post_call] Salesforce push failed: %s", exc)
    return False


def _map_intent_to_sf(intent_level: str) -> str:
    return {
        "hot": "Working - Contacted",
        "warm": "Open - Not Contacted",
        "cold": "Open - Not Contacted",
        "not_interested": "Closed - Not Converted",
    }.get(intent_level, "Open - Not Contacted")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SLACK  (Block Kit)
# ═══════════════════════════════════════════════════════════════════════════════

async def push_to_slack(
    *,
    bot_token: str,
    channel: str,
    lead_data: dict,
    extracted_vars: dict,
    call_summary: str,
    call_log_id: str,
    agent_name: str = "",
    caller_phone: str = "",
    duration: int = 0,
    sentiment: str = "neutral",
    sentiment_score: float = 0.0,
) -> bool:
    """
    Post a rich Block-Kit call summary to Slack.
    Requires: pip install slack-sdk
    Sentiment emojis: 😊 positive | 😐 neutral | 😠 negative
    """
    try:
        from slack_sdk.web.async_client import AsyncWebClient  # type: ignore

        client = AsyncWebClient(token=bot_token)
        s_emoji = {"positive": "😊", "negative": "😠", "neutral": "😐"}.get(sentiment, "😐")
        caller = caller_phone or lead_data.get("phone") or lead_data.get("name") or "Unknown"
        intent = lead_data.get("intent") or lead_data.get("call_outcome") or "unknown"
        mins, secs = divmod(duration or 0, 60)
        duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"

        blocks: list[dict] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{s_emoji} VoiceFlow — Call Summary"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Agent:* {agent_name or 'n/a'}"},
                    {"type": "mrkdwn", "text": f"*Caller:* {caller}"},
                    {"type": "mrkdwn", "text": f"*Duration:* {duration_str}"},
                    {"type": "mrkdwn", "text": f"*Intent:* {intent}"},
                    {"type": "mrkdwn", "text": f"*Sentiment:* {s_emoji} {sentiment.title()} ({sentiment_score:.2f})"},
                    {"type": "mrkdwn", "text": f"*Outcome:* {lead_data.get('call_outcome', 'n/a')}"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary*\n{call_summary[:900] or '_No summary_'}"},
            },
        ]

        # Extracted variables block
        all_vars = {**lead_data, **extracted_vars}
        skip = {"intent", "sentiment", "call_outcome", "intent_level", "follow_up_action", "objections"}
        var_lines = [
            f"• *{k.replace('_', ' ').title()}:* {v}"
            for k, v in all_vars.items()
            if v is not None and k not in skip
        ]
        if var_lines:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Extracted Data*\n" + "\n".join(var_lines[:20])},
            })

        if lead_data.get("follow_up_action"):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Next Step:* {lead_data['follow_up_action']}"},
            })

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Call ID: `{call_log_id}`"}],
        })

        await client.chat_postMessage(channel=channel, blocks=blocks, text=f"Call summary — {caller}")
        logger.info("[post_call] Slack message sent to %s", channel)
        return True
    except ImportError:
        logger.warning("[post_call] slack-sdk not installed. Run: pip install slack-sdk")
    except Exception as exc:
        logger.warning("[post_call] Slack push failed: %s", exc)
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 6. HMAC-SIGNED WEBHOOK
# ═══════════════════════════════════════════════════════════════════════════════

async def push_to_webhook(
    *,
    url: str,
    secret: str,
    call_id: str,
    agent_id: str,
    tenant_id: str,
    transcript: str,
    summary: str,
    sentiment_score: float,
    sentiment_label: str,
    extracted_variables: dict,
    lead_data: dict,
    recording_url: str,
    duration: int,
    label: str = "call.completed",
) -> bool:
    """
    POST HMAC-SHA256 signed webhook with full call payload.
    Headers: X-VoiceFlow-Signature (sha256 hex) + X-VoiceFlow-Timestamp
    Verifiable by Make, Zapier, n8n, custom endpoints.
    """
    from datetime import datetime, timezone

    payload = {
        "event": label,
        "call_id": call_id,
        "agent_id": agent_id,
        "tenant_id": tenant_id,
        "duration": duration,
        "transcript": transcript,
        "summary": summary,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "extracted_variables": extracted_variables,
        "lead_data": lead_data,
        "recording_url": recording_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body = json.dumps(payload, default=str).encode()
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), (ts + "." + body.decode()).encode(), hashlib.sha256).hexdigest() if secret else ""
    headers = {
        "Content-Type": "application/json",
        "X-VoiceFlow-Signature": sig,
        "X-VoiceFlow-Timestamp": ts,
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


# ═══════════════════════════════════════════════════════════════════════════════
# 7. GOHIGHLEVEL
# ═══════════════════════════════════════════════════════════════════════════════

async def push_to_gohighlevel(
    *,
    api_key: str,
    location_id: str,
    lead_data: dict,
    extracted_vars: dict,
    call_summary: str,
    call_log_id: str,
    caller_phone: str = "",
    duration: int = 0,
    workflow_id: Optional[str] = None,
) -> bool:
    """
    Create/update a GoHighLevel Contact, add a Note, optionally trigger a workflow.
    Uses GHL API v2 (https://services.leadconnectorhq.com).
    location_id: The GHL sub-account Location ID (required for v2 API calls).
    Requires: Private Integration Token or OAuth Access Token (Sub-Account scope).
    """
    base = "https://services.leadconnectorhq.com"
    phone = caller_phone or lead_data.get("phone", "")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Version": "2023-02-21",
    }
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            # Build contact payload for upsert (GHL v2 native upsert handles create/update)
            contact_payload: dict = {
                "locationId": location_id,
                "source": "VoiceFlow AI Call",
            }
            if phone:
                contact_payload["phone"] = phone
            if lead_data.get("name"):
                parts = (lead_data["name"] or "").split(" ", 1)
                contact_payload["firstName"] = parts[0]
                contact_payload["lastName"] = parts[1] if len(parts) > 1 else ""
            if lead_data.get("email"):
                contact_payload["email"] = lead_data["email"]
            if lead_data.get("company"):
                contact_payload["companyName"] = lead_data["company"]

            # Extracted vars as tags for easy filtering in GHL
            if extracted_vars:
                tags = [f"vf_{k}:{str(v)[:40]}" for k, v in extracted_vars.items() if v is not None]
                if tags:
                    contact_payload["tags"] = tags[:10]

            # Native upsert — GHL deduplicates by phone/email per location settings
            upsert_resp = await client.post(f"{base}/contacts/upsert", json=contact_payload)
            if upsert_resp.status_code not in (200, 201):
                logger.warning("[post_call] GHL upsert failed: %s %s", upsert_resp.status_code, upsert_resp.text[:200])
                return False

            contact_id = upsert_resp.json().get("contact", {}).get("id")
            if not contact_id:
                logger.warning("[post_call] GHL upsert returned no contact id")
                return False

            # Add a note (v2 path: /contacts/{id}/notes)
            duration_str = f"{duration // 60}m {duration % 60}s" if duration else "n/a"
            note_body = f"VoiceFlow Call\nCall ID: {call_log_id} | Duration: {duration_str}\n\n{call_summary}"
            await client.post(f"{base}/contacts/{contact_id}/notes", json={"body": note_body})

            # Optionally trigger a workflow (v2 path: /contacts/{id}/workflow/{workflowId})
            if workflow_id:
                await client.post(
                    f"{base}/contacts/{contact_id}/workflow/{workflow_id}",
                    json={"eventStartTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                )
                logger.info("[post_call] GHL workflow %s triggered for contact %s", workflow_id, contact_id)

            logger.info("[post_call] GHL contact upserted: %s", contact_id)
            return True
    except Exception as exc:
        logger.warning("[post_call] GHL push failed: %s", exc)
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

async def deliver_post_call(
    *,
    tenant_id: str,
    agent_id: str,
    call_log_id: str,
    transcript: str,
    analysis: dict,
    groq_key: Optional[str] = None,
    caller_phone: str = "",
    call_duration: int = 0,
    call_sid: str = "",
    recording_url: str = "",
) -> None:
    """
    Main entry point called after every call.

    1. Extract structured leads + agent-configured variables from transcript
    2. Deep-merge agent.integrations over tenant.settings.integrations
    3. Push to all enabled destinations in parallel
    4. Persist extractedVariables + recordingUrl to CallLog
    """
    from app.database import AsyncSessionLocal
    from app.models import Agent, Tenant, CallLog
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

    # Resolve Groq key
    if not groq_key:
        enc = (tenant.settings or {}).get("groqApiKey")
        groq_key = decrypt_safe(enc) if enc else app_settings.GROQ_API_KEY

    call_summary = analysis.get("summary", "")
    sentiment = analysis.get("sentiment", "neutral")
    sentiment_score = float(analysis.get("sentiment_score", 0.0))

    # Extract leads + agent-configured variables concurrently
    lead_data: dict = {}
    extracted_vars: dict = {}
    post_call_actions = (agent.llmPreferences or {}).get("post_call_actions", [])

    if groq_key and transcript:
        lead_task = extract_leads(transcript, groq_key)
        var_task = (
            extract_variables(transcript, post_call_actions, groq_key)
            if post_call_actions else asyncio.coroutine(lambda: {})()
        )
        lead_data, extracted_vars = await asyncio.gather(lead_task, var_task)

    sentiment_score = float(lead_data.get("sentiment_score", sentiment_score))

    # Deep-merge: tenant config as baseline, agent-level overrides per-key
    tenant_integrations: dict = (tenant.settings or {}).get("integrations", {})
    agent_integrations: dict = agent.integrations or {}
    integrations: dict = {**tenant_integrations}
    for key, val in agent_integrations.items():
        if isinstance(val, dict) and isinstance(integrations.get(key), dict):
            integrations[key] = {**integrations[key], **val}
        else:
            integrations[key] = val

    def _decr(v: str) -> str:
        return decrypt_safe(v) if v else ""

    tasks = []

    # Email
    email_cfg = integrations.get("email", {})
    if email_cfg.get("enabled") and (email_cfg.get("recipients") or email_cfg.get("to")):
        recipients = email_cfg.get("recipients") or email_cfg.get("to", [])
        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(",")]
        cfg = {**email_cfg, "recipients": recipients}
        if cfg.get("password"):
            cfg["password"] = _decr(cfg["password"])
        if cfg.get("api_key"):
            cfg["api_key"] = _decr(cfg["api_key"])
        tasks.append(push_to_email(
            email_config=cfg,
            agent_name=agent.name or "VoiceFlow Agent",
            lead_data=lead_data,
            extracted_vars=extracted_vars,
            call_summary=call_summary,
            duration=call_duration,
            call_log_id=call_log_id,
            sentiment=sentiment,
        ))

    # HubSpot
    hs = integrations.get("hubspot", {})
    if hs.get("enabled") and hs.get("accessToken"):
        tasks.append(push_to_hubspot(
            access_token=_decr(hs["accessToken"]),
            lead_data=lead_data,
            extracted_vars=extracted_vars,
            call_summary=call_summary,
            transcript=transcript,
            call_log_id=call_log_id,
            caller_phone=caller_phone,
            duration=call_duration,
            field_map=hs.get("fieldMap"),
            create_deal=hs.get("createDeal", False),
        ))

    # Salesforce
    sf = integrations.get("salesforce", {})
    if sf.get("enabled") and sf.get("username"):
        tasks.append(push_to_salesforce(
            instance_url=sf.get("instanceUrl", ""),
            username=sf["username"],
            password=_decr(sf.get("password", "")),
            security_token=_decr(sf.get("securityToken", "")),
            lead_data=lead_data,
            extracted_vars=extracted_vars,
            call_summary=call_summary,
            call_log_id=call_log_id,
            caller_phone=caller_phone,
            duration=call_duration,
            object_type=sf.get("objectType", "Lead"),
            field_map=sf.get("fieldMap"),
        ))

    # Slack
    slk = integrations.get("slack", {})
    if slk.get("enabled") and slk.get("botToken"):
        tasks.append(push_to_slack(
            bot_token=_decr(slk["botToken"]),
            channel=slk.get("channel", "#calls"),
            lead_data=lead_data,
            extracted_vars=extracted_vars,
            call_summary=call_summary,
            call_log_id=call_log_id,
            agent_name=agent.name or "",
            caller_phone=caller_phone,
            duration=call_duration,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
        ))

    # GoHighLevel
    ghl = integrations.get("gohighlevel", {})
    if ghl.get("enabled") and ghl.get("apiKey") and ghl.get("locationId"):
        tasks.append(push_to_gohighlevel(
            api_key=_decr(ghl["apiKey"]),
            location_id=ghl["locationId"],
            lead_data=lead_data,
            extracted_vars=extracted_vars,
            call_summary=call_summary,
            call_log_id=call_log_id,
            caller_phone=caller_phone,
            duration=call_duration,
            workflow_id=ghl.get("workflowId"),
        ))

    # Custom webhooks
    for wh in integrations.get("webhooks", []):
        if wh.get("url") and wh.get("enabled"):
            tasks.append(push_to_webhook(
                url=wh["url"],
                secret=wh.get("secret", ""),
                call_id=call_log_id,
                agent_id=agent_id,
                tenant_id=tenant_id,
                transcript=transcript,
                summary=call_summary,
                sentiment_score=sentiment_score,
                sentiment_label=sentiment,
                extracted_variables=extracted_vars,
                lead_data=lead_data,
                recording_url=recording_url,
                duration=call_duration,
                label=wh.get("label", "call.completed"),
            ))

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if r is True)
        logger.info(
            "[post_call] delivery complete call=%s — %d/%d targets succeeded",
            call_log_id, successes, len(tasks),
        )

    # Persist extracted data back to CallLog
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(CallLog).where(CallLog.id == call_log_id))
            log = result.scalar_one_or_none()
            if log:
                log.extractedVariables = extracted_vars
                if recording_url:
                    log.recordingUrl = recording_url
                log.analysis = {**(log.analysis or {}), "leadData": lead_data}
                await db.commit()
    except Exception as exc:
        logger.warning("[post_call] failed to persist extracted data: %s", exc)
