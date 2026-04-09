"""
/onboarding routes — mirrors Express src/routes/onboarding.ts
THE most critical routes for the demo flow.
"""
import logging
from typing import Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, AgentConfiguration, Tenant, Brand
from app.config import settings

logger = logging.getLogger("voiceflow.onboarding")
router = APIRouter()

# In-memory onboarding progress store (mirrors Express behavior)
_progress_store: dict[str, dict] = {}


# ── Company search (Clearbit) ────────────────────────────────────────────────

@router.get("/company-search")
async def company_search(q: str = Query("")):
    q = q.strip()
    if not q:
        return {"companies": []}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://autocomplete.clearbit.com/v1/companies/suggest?query={q}"
            )
            items = resp.json() if resp.status_code == 200 else []
        companies = [
            {
                "id": item.get("domain") or item.get("name", "").lower().replace(" ", "-"),
                "name": item.get("name", ""),
                "domain": item.get("domain", ""),
                "industry": "",
                "description": item.get("domain", ""),
            }
            for item in (items or [])[:10]
        ]
        return {"companies": companies}
    except Exception:
        logger.exception("Clearbit search failed")
        return {"companies": []}


# ── Company profile ──────────────────────────────────────────────────────────

@router.get("/company")
async def get_company(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}
    return {
        "company_name": s.get("companyName"),
        "industry": s.get("industry"),
        "use_case": s.get("useCase"),
        "website_url": s.get("websiteUrl"),
        "description": s.get("description"),
    }


@router.post("/company")
async def save_company(request: Request, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    body = await request.json()
    company_name = body.get("company_name")
    industry = body.get("industry")
    use_case = body.get("use_case")
    website_url = body.get("website_url")
    description = body.get("description")

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        tenant.settings = {
            "companyName": company_name,
            "industry": industry,
            "useCase": use_case,
            "websiteUrl": website_url or None,
            "description": description or None,
        }
        await db.commit()

    scrape_job_id: Optional[str] = None
    if website_url:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{settings.FASTAPI_URL}/ingest/company",
                    json={
                        "tenantId": auth.tenant_id,
                        "website_url": website_url,
                        "company_name": company_name or "",
                        "company_description": description,
                        "industry": industry,
                        "use_case": use_case,
                    },
                )
                scrape_job_id = resp.json().get("job_id")
        except Exception:
            logger.exception("Failed to trigger company scrape")

    return {"success": True, "scrapeJobId": scrape_job_id}


# ── Scrape status proxy ─────────────────────────────────────────────────────

@router.get("/scrape-status/{job_id}")
async def scrape_status(job_id: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.FASTAPI_URL}/status/{job_id}")
            return resp.json()
    except Exception:
        return JSONResponse({"error": "Failed to fetch scrape status"}, status_code=500)


# ── Company knowledge proxy ──────────────────────────────────────────────────

@router.get("/company-knowledge")
async def company_knowledge(auth: AuthContext = Depends(get_auth)):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.FASTAPI_URL}/knowledge/company/{auth.tenant_id}")
            return resp.json()
    except Exception:
        return JSONResponse({"error": "Failed to fetch company knowledge"}, status_code=500)


@router.delete("/company-knowledge/{chunk_id}")
async def delete_company_knowledge(chunk_id: str, auth: AuthContext = Depends(get_auth)):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.delete(f"{settings.FASTAPI_URL}/knowledge/{auth.tenant_id}/{chunk_id}")
        return {"deleted": True}
    except Exception:
        return JSONResponse({"error": "Failed to delete chunk"}, status_code=500)


# ── Agent creation ───────────────────────────────────────────────────────────

@router.post("/agent")
async def create_agent(request: Request, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    body = await request.json()
    name = body.get("name", "Unnamed Agent")
    role = body.get("role")
    template_id = body.get("templateId")
    description = body.get("description")
    channels = body.get("channels")
    brand_id = body.get("brandId")

    if brand_id:
        r = await db.execute(select(Brand).where(Brand.id == brand_id, Brand.tenantId == auth.tenant_id))
        if not r.scalar_one_or_none():
            return JSONResponse({"error": "Brand not found or does not belong to this tenant"}, status_code=400)

    agent = Agent(
        name=name,
        description=description or role or None,
        templateId=template_id or None,
        brandId=brand_id or None,
        channels=channels or None,
        userId=auth.user_id,
        tenantId=auth.tenant_id,
    )
    db.add(agent)
    await db.flush()

    # Get tenant settings for company info
    tr = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tr.scalar_one_or_none()
    tenant_settings = (tenant.settings or {}) if tenant else {}

    config = AgentConfiguration(
        agentId=agent.id,
        templateId=template_id or None,
        agentName=name,
        agentRole=role or None,
        agentDescription=description or None,
        communicationChannels=channels or None,
        companyName=tenant_settings.get("companyName"),
        industry=tenant_settings.get("industry"),
        primaryUseCase=tenant_settings.get("useCase"),
    )
    db.add(config)
    await db.commit()

    return {"agent_id": agent.id}


# ── Knowledge upload ─────────────────────────────────────────────────────────

@router.post("/knowledge")
async def upload_knowledge(
    request: Request,
    auth: AuthContext = Depends(get_auth),
):
    form = await request.form()
    files = form.getlist("files")
    websites = form.get("websites")
    faq_text = form.get("faq_text")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            data = {"tenant_id": auth.tenant_id, "user_id": auth.user_id}
            if websites:
                data["websites"] = websites
            if faq_text:
                data["faq_text"] = faq_text

            upload_files = []
            for f in files:
                if hasattr(f, "read"):
                    content = await f.read()
                    upload_files.append(("files", (f.filename, content, f.content_type or "application/octet-stream")))

            resp = await client.post(
                f"{settings.FASTAPI_URL}/ingest",
                data=data,
                files=upload_files if upload_files else None,
            )
            job_id = resp.json().get("job_id")
        return {"success": True, "jobId": job_id}
    except Exception:
        logger.exception("Error uploading knowledge")
        return JSONResponse({"error": "Internal server error"}, status_code=500)


# ── Voice configuration ──────────────────────────────────────────────────────

@router.post("/voice")
async def configure_voice(request: Request, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    body = await request.json()
    voice = body.get("voice")
    tone = body.get("tone")
    personality = body.get("personality")

    result = await db.execute(
        select(Agent).where(Agent.tenantId == auth.tenant_id).order_by(Agent.createdAt.desc()).limit(1)
    )
    agent = result.scalar_one_or_none()

    if agent:
        cr = await db.execute(select(AgentConfiguration).where(AgentConfiguration.agentId == agent.id))
        config = cr.scalar_one_or_none()
        if config:
            if voice:
                config.voiceId = voice
            if tone:
                config.responseTone = tone
            if personality:
                config.preferredResponseStyle = personality
        else:
            config = AgentConfiguration(
                agentId=agent.id,
                voiceId=voice or None,
                responseTone=tone or None,
                preferredResponseStyle=personality or None,
            )
            db.add(config)
        await db.commit()

    return {"success": True}


# ── Channel setup ────────────────────────────────────────────────────────────

@router.post("/channels")
async def setup_channels():
    return {"success": True}


# ── Agent configuration ──────────────────────────────────────────────────────

@router.post("/agent-config")
async def agent_config(request: Request, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    body = await request.json()

    result = await db.execute(
        select(Agent).where(Agent.tenantId == auth.tenant_id).order_by(Agent.createdAt.desc()).limit(1)
    )
    agent = result.scalar_one_or_none()

    if agent:
        cr = await db.execute(select(AgentConfiguration).where(AgentConfiguration.agentId == agent.id))
        config = cr.scalar_one_or_none()

        fields = {
            "agentName": body.get("agent_name"),
            "agentRole": body.get("agent_role"),
            "agentDescription": body.get("agent_description"),
            "personalityTraits": body.get("personality_traits"),
            "communicationChannels": body.get("communication_channels"),
            "preferredResponseStyle": body.get("preferred_response_style"),
            "responseTone": body.get("response_tone"),
            "voiceId": body.get("voice_id"),
            "companyName": body.get("company_name"),
            "industry": body.get("industry"),
            "primaryUseCase": body.get("primary_use_case"),
        }

        if config:
            for k, v in fields.items():
                if v is not None:
                    setattr(config, k, v)
        else:
            config = AgentConfiguration(agentId=agent.id, **{k: v for k, v in fields.items() if v is not None})
            db.add(config)
        await db.commit()

    return {
        "success": True,
        "message": "Agent configured successfully",
        "agent_id": agent.id if agent else "unknown",
        "chroma_collection": f"collection_{auth.tenant_id}",
    }


# ── Deploy agent ─────────────────────────────────────────────────────────────

@router.post("/deploy")
async def deploy_agent(request: Request, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    body = await request.json()
    agent_id = body.get("agent_id")
    if not agent_id:
        return JSONResponse({"error": "agent_id is required"}, status_code=400)

    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    if agent.phoneNumber:
        return {"success": True, "phone_number": agent.phoneNumber, "already_provisioned": True}

    # Check Twilio credentials
    tr = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = tr.scalar_one_or_none()
    tenant_settings = (tenant.settings or {}) if tenant else {}
    if not tenant_settings.get("twilioAccountSid") or not tenant_settings.get("twilioAuthToken"):
        return JSONResponse(
            {
                "error": "Twilio credentials not configured. Please add your Twilio Account SID and Auth Token in Settings.",
                "code": "TWILIO_NOT_CONFIGURED",
            },
            status_code=400,
        )

    # In demo mode, just return a mock number
    agent.status = "active"
    await db.commit()
    return {"success": True, "phone_number": "+1-555-DEMO", "already_provisioned": False}


# ── Status ───────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    return {"status": "ready", "message": "Agent is ready for deployment"}


# ── Onboarding progress (in-memory, same as Express) ────────────────────────

@router.post("/progress")
async def save_progress(request: Request, auth: AuthContext = Depends(get_auth)):
    body = await request.json()
    _progress_store[auth.user_id] = {
        "agent_id": body.get("agent_id"),
        "current_step": body.get("current_step"),
        "data": body.get("data"),
    }
    return {
        "success": True,
        "agent_id": body.get("agent_id"),
        "current_step": body.get("current_step"),
        "data": body.get("data"),
    }


@router.get("/progress")
async def get_progress(auth: AuthContext = Depends(get_auth)):
    progress = _progress_store.get(auth.user_id)
    if progress:
        return {"exists": True, **progress}
    return {"exists": False}


@router.delete("/progress")
async def delete_progress(auth: AuthContext = Depends(get_auth)):
    _progress_store.pop(auth.user_id, None)
    return {"deleted": True}
