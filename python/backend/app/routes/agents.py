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

