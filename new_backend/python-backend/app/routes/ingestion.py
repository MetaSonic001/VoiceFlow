"""
/api/ingestion routes — mirrors Express src/routes/ingestion.ts
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Agent, Document
from app.config import settings

router = APIRouter()


@router.post("/start")
async def start_ingestion(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    agent_id = body.get("agentId", "knowledge_base")
    urls = body.get("urls", [])
    s3_urls = body.get("s3Urls", [])

    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        result2 = await db.execute(select(Agent).where(Agent.tenantId == auth.tenant_id).limit(1))
        agent = result2.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "No agents found for this tenant"}, status_code=403)

    documents = []
    for url in urls:
        doc = Document(url=url, agentId=agent.id, tenantId=auth.tenant_id, status="pending")
        db.add(doc)
        await db.flush()
        documents.append({"id": doc.id, "url": doc.url, "status": doc.status})

    for s3_url in s3_urls:
        doc = Document(s3Path=s3_url, agentId=agent.id, tenantId=auth.tenant_id, status="pending")
        db.add(doc)
        await db.flush()
        documents.append({"id": doc.id, "s3Path": doc.s3Path, "status": doc.status})

    await db.commit()

    job_id = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.FASTAPI_URL}/ingest",
                json={"tenantId": auth.tenant_id, "agentId": agent.id, "urls": urls, "s3_urls": s3_urls},
            )
            job_id = resp.json().get("job_id")
    except Exception:
        pass

    return {"jobId": job_id, "documents": documents, "status": "processing"}


@router.get("/status/{job_id}")
async def ingestion_status(job_id: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.FASTAPI_URL}/status/{job_id}")
            return resp.json()
    except Exception:
        return JSONResponse({"error": "Failed to fetch status"}, status_code=500)


@router.get("/jobs")
async def ingestion_jobs(agentId: str = Query(...), auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Agent).where(Agent.id == agentId, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)
    # Simplified: return empty list since we don't have Redis job tracking
    return []
