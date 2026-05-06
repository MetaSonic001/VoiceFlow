"""
/api/agents routes — mirrors Express src/routes/agents.ts
GET /, GET /:id, POST /, PUT /:id, DELETE /:id
"""
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, Document, User

router = APIRouter()


def _agent_to_dict(agent: Agent, doc_count: int = 0) -> dict:
    return {
        "id": agent.id,
        "tenantId": agent.tenantId,
        "brandId": agent.brandId,
        "userId": agent.userId,
        "templateId": agent.templateId,
        "name": agent.name,
        "status": agent.status,
        "description": agent.description,
        "systemPrompt": agent.systemPrompt,
        "voiceType": agent.voiceType,
        "channels": agent.channels,
        "llmPreferences": agent.llmPreferences,
        "tokenLimit": agent.tokenLimit,
        "contextWindowStrategy": agent.contextWindowStrategy,
        "phoneNumber": agent.phoneNumber,
        "twilioNumberSid": agent.twilioNumberSid,
        "totalCalls": agent.totalCalls,
        "totalChats": agent.totalChats,
        "successRate": agent.successRate,
        "avgResponseTime": agent.avgResponseTime,
        "chromaCollection": agent.chromaCollection,
        "configPath": agent.configPath,
        # Prompt-to-Agent structured fields
        "contextBreakdown": agent.context_breakdown,
        "welcomeMessage": agent.welcome_message,
        "postCallActions": agent.post_call_actions,
        "languageConfig": agent.language_config,
        "callerPersonas": agent.caller_personas,
        "simulationSuite": agent.simulation_suite,
        "deploymentReadinessScore": agent.deployment_readiness_score,
        "versionNumber": agent.version_number,
        "createdAt": agent.createdAt.isoformat() if agent.createdAt else None,
        "updatedAt": agent.updatedAt.isoformat() if agent.updatedAt else None,
        "_count": {"documents": doc_count},
    }


@router.get("/")
async def list_agents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    where = [
        Agent.tenantId == auth.tenant_id,
        or_(Agent.userId == auth.user_id, Agent.userId.is_(None)),
    ]
    if search:
        where.append(Agent.name.ilike(f"%{search}%"))
    if status:
        where.append(Agent.status == status)

    total_q = select(func.count(Agent.id)).where(*where)
    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    agents_q = (
        select(Agent)
        .where(*where)
        .order_by(Agent.createdAt.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    agents_result = await db.execute(agents_q)
    agents = agents_result.scalars().all()

    # Get document counts
    agent_ids = [a.id for a in agents]
    doc_counts: dict[str, int] = {}
    if agent_ids:
        dc_q = (
            select(Document.agentId, func.count(Document.id))
            .where(Document.agentId.in_(agent_ids))
            .group_by(Document.agentId)
        )
        dc_result = await db.execute(dc_q)
        doc_counts = dict(dc_result.all())

    return {
        "agents": [_agent_to_dict(a, doc_counts.get(a.id, 0)) for a in agents],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Get documents
    docs_q = select(Document).where(Document.agentId == agent_id).order_by(Document.createdAt.desc())
    docs_result = await db.execute(docs_q)
    docs = docs_result.scalars().all()

    d = _agent_to_dict(agent, len(docs))
    d["documents"] = [
        {
            "id": doc.id,
            "url": doc.url,
            "s3Path": doc.s3Path,
            "status": doc.status,
            "title": doc.title,
            "createdAt": doc.createdAt.isoformat() if doc.createdAt else None,
        }
        for doc in docs
    ]
    return d


@router.post("/")
async def create_agent(request_data: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    name = request_data.get("name")
    if not name:
        return JSONResponse({"error": "\"name\" is required"}, status_code=400)

    agent = Agent(
        name=name,
        description=request_data.get("description", ""),
        systemPrompt=request_data.get("systemPrompt", ""),
        voiceType=request_data.get("voiceType", "female"),
        llmPreferences=request_data.get("llmPreferences", {"model": "llama-3.3-70b-versatile"}),
        tokenLimit=request_data.get("tokenLimit", 4096),
        contextWindowStrategy=request_data.get("contextWindowStrategy", "condense"),
        channels=request_data.get("channels"),
        templateId=request_data.get("templateId"),
        tenantId=auth.tenant_id,
        userId=auth.user_id,
    )
    db.add(agent)
    await db.flush()
    await db.commit()
    await db.refresh(agent)
    return JSONResponse(_agent_to_dict(agent), status_code=201)


@router.put("/{agent_id}")
async def update_agent(agent_id: str, request_data: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    for field in ("name", "description", "systemPrompt", "voiceType", "llmPreferences",
                   "tokenLimit", "contextWindowStrategy", "channels", "status", "phoneNumber", "brandId"):
        if field in request_data:
            setattr(agent, field, request_data[field])

    await db.commit()
    await db.refresh(agent)
    return _agent_to_dict(agent)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    await db.delete(agent)
    await db.commit()
    return Response(status_code=204)


@router.put("/{agent_id}/telephony")
async def update_telephony(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update telephony_provider for an agent (twilio-gather | twilio-stream | twilio-whatsapp)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    body = await request.json()
    provider = (body.get("telephonyProvider") or "").strip()
    allowed = {"twilio-gather", "twilio-stream", "twilio-whatsapp"}
    if provider and provider not in allowed:
        return JSONResponse({"error": f"Invalid provider. Must be one of: {', '.join(sorted(allowed))}"}, status_code=400)

    if provider:
        agent.telephony_provider = provider
    await db.commit()
    await db.refresh(agent)
    return {"id": agent.id, "telephonyProvider": agent.telephony_provider}


@router.post("/{agent_id}/whatsapp")
async def configure_whatsapp(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Save WhatsApp configuration into agent.channels."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    body = await request.json()
    whatsapp_number = (body.get("whatsapp_number") or "").strip()
    messaging_sid = (body.get("twilio_messaging_sid") or "").strip()

    channels: dict = agent.channels or {}
    channels["whatsapp"] = {
        "enabled": bool(whatsapp_number),
        "whatsapp_number": whatsapp_number,
        "twilio_messaging_sid": messaging_sid,
    }
    agent.channels = channels
    await db.commit()
    await db.refresh(agent)
    return {
        "id": agent.id,
        "whatsapp": channels["whatsapp"],
        "webhookUrl": f"/api/whatsapp/inbound/{agent.id}",
    }


@router.post("/{agent_id}/activate")
async def activate_agent(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    agent.status = "active"
    await db.commit()
    return {"success": True}


@router.post("/generate-from-prompt")
async def generate_agent_from_prompt(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Prompt-based agent creation: "describe your agent in one sentence → auto-fills all fields."

    Mirrors OmniDimension's one-line agent creation flow.
    The LLM returns a complete agent config that can be used to pre-fill the wizard
    or create the agent directly with create=true.

    Request body:
    {
      "prompt": "A friendly sales agent for our SaaS startup that qualifies leads and books demos",
      "create": false    // if true, also creates the agent immediately and returns its id
    }

    Returns:
    {
      "name": "Sales Lead Qualifier",
      "description": "...",
      "systemPrompt": "...",
      "voiceType": "female",
      "templateId": "cold-calling",
      "llmPreferences": {"model": "llama-3.3-70b-versatile"},
      "suggestedKnowledgeTopics": [...],
      "suggestedChannels": ["voice", "whatsapp"],
      "agentId": "..."    // only if create=true
    }
    """
    from app.models import Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    import httpx, json

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()[:500]
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    do_create = bool(body.get("create", False))

    # Resolve Groq key
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    if not groq_key:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=503)

    generation_prompt = f"""Given this agent description, generate a complete VoiceFlow agent configuration.
Return ONLY valid JSON — no markdown, no explanation.

DESCRIPTION: "{prompt}"

Generate JSON with exactly these fields:
{{
  "name": "short 2-4 word agent name",
  "description": "one sentence description",
  "systemPrompt": "full system prompt (3-5 sentences, professional tone, defines persona, goals, constraints)",
  "voiceType": "male" or "female",
  "templateId": one of: "customer-support" | "cold-calling" | "appointment-setter" | "healthcare" | "real-estate" | "e-commerce" | "lead-qualification" | "faq-bot" | "hr-recruiter" | "debt-collection",
  "llmPreferences": {{"model": "llama-3.3-70b-versatile"}},
  "tokenLimit": 4096,
  "suggestedKnowledgeTopics": ["list", "of", "3-5 knowledge base topics to upload"],
  "suggestedChannels": ["voice and/or whatsapp and/or chat"],
  "sttEngine": "faster-whisper" or "sarvam" (use sarvam if Indian language context detected),
  "ttsEngine": "kokoro" or "sarvam" (use sarvam if Indian language context detected),
  "ttsLanguageCode": "en-IN" or relevant language code if non-English detected
}}"""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are an expert at configuring AI voice agents. Return valid JSON only."},
                        {"role": "user", "content": generation_prompt},
                    ],
                    "temperature": 0.4,
                    "max_tokens": 1024,
                },
            )
    except Exception as exc:
        return JSONResponse({"error": f"LLM request failed: {exc}"}, status_code=503)

    if resp.status_code != 200:
        return JSONResponse({"error": f"LLM returned {resp.status_code}"}, status_code=503)

    content = resp.json()["choices"][0]["message"]["content"].strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        agent_config: dict = json.loads(content)
    except json.JSONDecodeError:
        return JSONResponse({"error": "LLM returned invalid JSON", "raw": content[:500]}, status_code=500)

    if do_create:
        agent = Agent(
            name=agent_config.get("name", "New Agent"),
            description=agent_config.get("description", ""),
            systemPrompt=agent_config.get("systemPrompt", ""),
            voiceType=agent_config.get("voiceType", "female"),
            templateId=agent_config.get("templateId"),
            llmPreferences=agent_config.get("llmPreferences", {"model": "llama-3.3-70b-versatile"}),
            tokenLimit=agent_config.get("tokenLimit", 4096),
            tenantId=auth.tenant_id,
            userId=auth.user_id,
        )
        db.add(agent)
        await db.flush()
        await db.commit()
        await db.refresh(agent)
        agent_config["agentId"] = agent.id

    return JSONResponse(agent_config, status_code=201 if do_create else 200)


@router.post("/generate-from-prompt/revise")
async def revise_agent_from_prompt(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Revise an existing agent's configuration based on a follow-up prompt.

    Implements per-prompt agent revision: the LLM receives the current config
    and the delta instruction, and returns ONLY the fields that should change.
    Manually edited fields not mentioned in the revision prompt are preserved.

    Body:
    {
      "agent_id": "...",
      "revision_prompt": "make it more formal and also handle insurance queries",
      "apply": false  // if true, immediately patches the agent in DB
    }
    """
    from app.models import Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    import httpx, json as json_mod

    body = await request.json()
    revision_prompt = (body.get("revision_prompt") or "").strip()[:500]
    agent_id = body.get("agent_id", "")
    apply = bool(body.get("apply", False))

    if not revision_prompt:
        return JSONResponse({"error": "revision_prompt is required"}, status_code=400)
    if not agent_id:
        return JSONResponse({"error": "agent_id is required"}, status_code=400)

    # Fetch current agent
    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    current_config = {
        "name": agent.name,
        "description": agent.description,
        "systemPrompt": agent.systemPrompt,
        "voiceType": agent.voiceType,
        "llmPreferences": agent.llmPreferences,
        "tokenLimit": agent.tokenLimit,
    }

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    if not groq_key:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=503)

    revision_llm_prompt = f"""You are revising an AI voice agent configuration.

CURRENT CONFIGURATION:
{json_mod.dumps(current_config, indent=2)}

REVISION INSTRUCTION: "{revision_prompt}"

Return a JSON object containing ONLY the fields that need to change.
Do NOT include fields that should remain unchanged.
Preserve manual work — only update what the instruction explicitly mentions
or what must logically change as a consequence.

Example output if only the system prompt and tone need to change:
{{
  "systemPrompt": "revised prompt here...",
  "voiceType": "male"
}}

Return valid JSON only, no markdown."""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are an expert agent configurator. Return valid JSON only with changed fields."},
                        {"role": "user", "content": revision_llm_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
            )
    except Exception as exc:
        return JSONResponse({"error": f"LLM request failed: {exc}"}, status_code=503)

    content = resp.json()["choices"][0]["message"]["content"].strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        delta: dict = json_mod.loads(content)
    except Exception:
        return JSONResponse({"error": "LLM returned invalid JSON", "raw": content[:500]}, status_code=500)

    if apply:
        for field in ("name", "description", "systemPrompt", "voiceType",
                      "llmPreferences", "tokenLimit", "channels"):
            if field in delta:
                setattr(agent, field, delta[field])
        await db.commit()
        await db.refresh(agent)
        delta["agentId"] = agent.id
        delta["applied"] = True

    return JSONResponse({"delta": delta, "applied": bool(delta.get("applied"))}, status_code=200)


@router.post("/generate-from-prompt/faqs")
async def generate_faqs_for_agent(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-generate a starter FAQ set and simulation test suite for an agent.

    Body:
    {
      "agent_id": "...",  // optional — uses existing agent's description + prompt
      "description": "dental clinic agent that books appointments in Hindi",  // or freeform
      "faq_count": 10,
      "simulation_count": 8
    }

    Returns:
    {
      "faqs": [{"question": "...", "answer": "..."}],
      "simulation_scenarios": [{"utterance": "...", "expected_intent": "..."}]
    }
    """
    from app.models import Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    import httpx, json as json_mod, asyncio as asyncio_mod

    body = await request.json()
    agent_id = body.get("agent_id", "")
    description = body.get("description", "")
    faq_count = min(int(body.get("faq_count", 10)), 30)
    sim_count = min(int(body.get("simulation_count", 8)), 20)

    if agent_id:
        agent_res = await db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
        )
        agent = agent_res.scalar_one_or_none()
        if agent:
            description = description or f"{agent.description or agent.name}. {agent.systemPrompt or ''}"

    if not description:
        return JSONResponse({"error": "description or agent_id is required"}, status_code=400)

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    if not groq_key:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=503)

    faq_prompt = f"""Generate {faq_count} realistic FAQ pairs for this AI voice agent.
Agent context: {description[:600]}
Return a JSON array with items: {{"question": "...", "answer": "..."}}
Questions should be what real callers would actually ask. Answers should be 1-2 sentences.
Return valid JSON array only."""

    sim_prompt = f"""Generate {sim_count} simulation test scenarios for this AI voice agent.
Agent context: {description[:600]}
Include a mix of: common requests, edge cases, short utterances, polite negations.
Return a JSON array with items:
{{"utterance": "...", "expected_intent": "...", "expected_keywords": ["list"], "must_not_contain": ["list"]}}
Return valid JSON array only."""

    async def _call(prompt: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                    "max_tokens": 2048,
                },
            )
        return r.json()["choices"][0]["message"]["content"].strip() if r.status_code == 200 else "[]"

    faq_raw, sim_raw = await asyncio_mod.gather(_call(faq_prompt), _call(sim_prompt))

    def _parse_json_list(raw: str) -> list:
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            start, end = raw.find("["), raw.rfind("]") + 1
            return json_mod.loads(raw[start:end]) if start >= 0 and end > start else []
        except Exception:
            return []

    return JSONResponse({
        "faqs": _parse_json_list(faq_raw),
        "simulation_scenarios": _parse_json_list(sim_raw),
    })




@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    agent.status = "paused"
    await db.commit()
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT-TO-AGENT 2.0 — Structured generation endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/generate-from-prompt/preview")
async def preview_agent_from_prompt(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1 + 2 of Prompt-to-Agent: extract intent, generate full structured config.
    Does NOT write to the database — returns a preview for the wizard UI.

    Optionally pass extract_only=true to skip full config generation (live intent chips).

    Body:
    {
      "prompt": "A dental clinic agent that books appointments in Hindi",
      "extract_only": false   // true → returns just intent extraction (fast, for live chips)
    }
    """
    from app.models import Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    from app.services.agent_builder_service import (
        extract_intent, generate_full_config, score_all_sections,
    )

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()[:1000]
    extract_only = bool(body.get("extract_only", False))

    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        from app.services.credentials import decrypt_safe as _ds
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = _ds(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    if not groq_key:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=503)

    intent = await extract_intent(prompt, groq_key)

    if extract_only:
        return JSONResponse({"intent": intent}, status_code=200)

    try:
        config = await generate_full_config(intent, prompt, groq_key)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)

    # Score sections in parallel
    sections = config.get("context_breakdown") or []
    if sections:
        config["context_breakdown"] = await score_all_sections(sections, groq_key)

    return JSONResponse({"intent": intent, "config": config}, status_code=200)


@router.post("/generate-from-prompt/create")
async def create_agent_from_preview(
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 4 of Prompt-to-Agent: create the agent from a confirmed preview config,
    then auto-generate a simulation suite and compute deployment readiness score.

    Body:
    {
      "config": { ... full preview config returned by /preview ... },
      "auto_simulate": true   // auto-generate simulation suite after creation
    }
    """
    from app.models import AgentVersion
    from app.services.agent_builder_service import (
        generate_simulation_suite, score_deployment_readiness, build_snapshot,
    )
    import json as _json

    body = await request.json()
    config = body.get("config") or {}
    auto_simulate = bool(body.get("auto_simulate", True))

    name = (config.get("name") or "New Agent")[:100]
    if not name:
        return JSONResponse({"error": "config.name is required"}, status_code=400)

    # Build flat systemPrompt from context_breakdown sections
    sections = config.get("context_breakdown") or []
    if sections:
        system_prompt_parts = []
        for s in sections:
            if s.get("is_enabled", True):
                system_prompt_parts.append(f"## {s['title']}\n{s.get('body', '')}")
        system_prompt = "\n\n".join(system_prompt_parts)
    else:
        system_prompt = config.get("system_prompt") or config.get("systemPrompt") or ""

    agent = Agent(
        name=name,
        description=config.get("description", ""),
        systemPrompt=system_prompt,
        voiceType=config.get("voice_type") or config.get("voiceType") or "female",
        templateId=config.get("template_id") or config.get("templateId"),
        llmPreferences=config.get("llm_preferences") or {"model": "llama-3.3-70b-versatile"},
        tokenLimit=4096,
        context_breakdown=sections,
        welcome_message=config.get("welcome_message", ""),
        post_call_actions=config.get("post_call_actions", []),
        language_config=config.get("language_config"),
        caller_personas=config.get("caller_personas", []),
        version_number=1,
        tenantId=auth.tenant_id,
        userId=auth.user_id,
    )
    db.add(agent)
    await db.flush()

    sim_suite: list = []
    readiness: dict = {}

    if auto_simulate:
        from app.models import Tenant
        from app.services.credentials import decrypt_safe
        from app.config import settings as app_settings

        tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
        tenant = tenant_res.scalar_one_or_none()
        groq_key = app_settings.GROQ_API_KEY
        if tenant and tenant.settings:
            enc = tenant.settings.get("groqApiKey")
            if enc:
                decrypted = decrypt_safe(enc)
                if decrypted and decrypted.startswith("gsk_"):
                    groq_key = decrypted

        if groq_key:
            sim_suite = await generate_simulation_suite(
                {**config, "use_cases": (config.get("language_config") or {}).get("use_cases") or []},
                groq_key,
                count=10,
            )
            agent.simulation_suite = sim_suite
            agent_dict_for_readiness = {**config, "simulation_suite": sim_suite}
            readiness = await score_deployment_readiness(agent_dict_for_readiness, groq_key=groq_key)
            agent.deployment_readiness_score = readiness.get("score")

    # Save initial version snapshot
    snapshot = build_snapshot(agent)
    version = AgentVersion(
        agentId=agent.id,
        tenantId=auth.tenant_id,
        versionNumber=1,
        changeDescription="Initial creation via Prompt-to-Agent",
        snapshot=snapshot,
    )
    db.add(version)

    await db.commit()
    await db.refresh(agent)

    return JSONResponse({
        "agentId": agent.id,
        "agent": _agent_to_dict(agent),
        "simulation_suite": sim_suite,
        "deployment_readiness": readiness,
    }, status_code=201)


@router.get("/{agent_id}/versions")
async def list_agent_versions(
    agent_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all saved versions for an agent."""
    from app.models import AgentVersion

    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    if not agent_res.scalar_one_or_none():
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    versions_res = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agentId == agent_id)
        .order_by(AgentVersion.versionNumber.desc())
    )
    versions = versions_res.scalars().all()
    return JSONResponse([{
        "id": v.id,
        "versionNumber": v.versionNumber,
        "changeDescription": v.changeDescription,
        "createdAt": v.createdAt.isoformat() if v.createdAt else None,
    } for v in versions])


@router.post("/{agent_id}/versions")
async def save_agent_version(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Save the current agent state as a named version snapshot."""
    from app.models import AgentVersion
    from app.services.agent_builder_service import build_snapshot

    body = await request.json()
    description = (body.get("description") or "Manual save")[:255]

    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Increment version number
    agent.version_number = (agent.version_number or 1) + 1
    version = AgentVersion(
        agentId=agent.id,
        tenantId=auth.tenant_id,
        versionNumber=agent.version_number,
        changeDescription=description,
        snapshot=build_snapshot(agent),
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    return JSONResponse({
        "id": version.id,
        "versionNumber": version.versionNumber,
        "changeDescription": version.changeDescription,
        "createdAt": version.createdAt.isoformat() if version.createdAt else None,
    }, status_code=201)


@router.post("/{agent_id}/versions/{version_id}/restore")
async def restore_agent_version(
    agent_id: str,
    version_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Restore an agent to a specific version snapshot."""
    from app.models import AgentVersion

    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    ver_res = await db.execute(
        select(AgentVersion).where(AgentVersion.id == version_id, AgentVersion.agentId == agent_id)
    )
    version = ver_res.scalar_one_or_none()
    if not version:
        return JSONResponse({"error": "Version not found"}, status_code=404)

    snap = version.snapshot or {}
    for field, col in [
        ("name", "name"), ("description", "description"), ("systemPrompt", "systemPrompt"),
        ("voiceType", "voiceType"), ("channels", "channels"), ("llmPreferences", "llmPreferences"),
        ("tokenLimit", "tokenLimit"), ("contextWindowStrategy", "contextWindowStrategy"),
        ("context_breakdown", "context_breakdown"), ("welcome_message", "welcome_message"),
        ("post_call_actions", "post_call_actions"), ("language_config", "language_config"),
        ("caller_personas", "caller_personas"), ("simulation_suite", "simulation_suite"),
    ]:
        if field in snap:
            setattr(agent, col, snap[field])

    await db.commit()
    await db.refresh(agent)
    return JSONResponse({"success": True, "restoredVersion": version.versionNumber, "agent": _agent_to_dict(agent)})


@router.post("/{agent_id}/revision-diff")
async def get_revision_diff(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute a structured diff for a revision prompt without applying changes.
    Returns change list per field/section so the UI can show a diff view.

    Body: {"revision_prompt": "make it more formal and add insurance query handling"}
    """
    from app.models import Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    from app.services.agent_builder_service import compute_revision_diff, build_snapshot

    body = await request.json()
    revision_prompt = (body.get("revision_prompt") or "").strip()[:500]
    if not revision_prompt:
        return JSONResponse({"error": "revision_prompt is required"}, status_code=400)

    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    if not groq_key:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=503)

    current = build_snapshot(agent)
    diff = await compute_revision_diff(current, revision_prompt, groq_key)
    return JSONResponse(diff)


@router.post("/{agent_id}/auto-simulate")
async def auto_simulate_agent(
    agent_id: str,
    request: Request,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    (Re-)generate a simulation suite for an existing agent and store it.
    Also recomputes deployment readiness score.

    Body: {"count": 10}
    """
    from app.models import Tenant
    from app.services.credentials import decrypt_safe
    from app.config import settings as app_settings
    from app.services.agent_builder_service import (
        generate_simulation_suite, score_deployment_readiness, build_snapshot,
    )

    body = await request.json()
    count = min(int(body.get("count", 10)), 20)

    agent_res = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id)
    )
    agent = agent_res.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    tenant_res = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tenant_res.scalar_one_or_none()
    groq_key = app_settings.GROQ_API_KEY
    if tenant and tenant.settings:
        enc = tenant.settings.get("groqApiKey")
        if enc:
            decrypted = decrypt_safe(enc)
            if decrypted and decrypted.startswith("gsk_"):
                groq_key = decrypted

    if not groq_key:
        return JSONResponse({"error": "No Groq API key configured"}, status_code=503)

    config = build_snapshot(agent)
    sim_suite = await generate_simulation_suite(config, groq_key, count=count)
    agent.simulation_suite = sim_suite

    config_with_suite = {**config, "simulation_suite": sim_suite}
    readiness = await score_deployment_readiness(config_with_suite, groq_key=groq_key)
    agent.deployment_readiness_score = readiness.get("score")

    await db.commit()
    return JSONResponse({
        "simulation_suite": sim_suite,
        "deployment_readiness": readiness,
    })

