"""
/api/ingestion routes — mirrors Express src/routes/ingestion.ts
Uses integrated ingestion service (Docling + PaddleOCR + ChromaDB + BM25).
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.auth import AuthContext, get_auth
from app.models import Agent, Document
from app.config import settings
from app.services.ingestion_service import (
    ingest_urls,
    ingest_file,
    ingest_company_website,
    ingest_s3_file,
    get_job_status,
)

router = APIRouter()


@router.post("/start")
async def start_ingestion(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """
    Start document ingestion for URLs and/or S3 files.
    Creates Document records and triggers background ingestion.
    """
    agent_id = body.get("agentId", "knowledge_base")
    urls = body.get("urls", [])
    s3_urls = body.get("s3Urls", [])

    # Validate agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        result2 = await db.execute(select(Agent).where(Agent.tenantId == auth.tenant_id).limit(1))
        agent = result2.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "No agents found for this tenant"}, status_code=403)

    # Create document records
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

    job_id = str(uuid.uuid4())

    # Run ingestion in background
    async def _background_ingest():
        try:
            if urls:
                result = await ingest_urls(
                    urls=urls,
                    tenant_id=auth.tenant_id,
                    agent_id=agent.id,
                    job_id=job_id,
                )
            for s3_url in s3_urls:
                await ingest_s3_file(
                    s3_path=s3_url,
                    tenant_id=auth.tenant_id,
                    agent_id=agent.id,
                    job_id=job_id,
                )
            # Update document statuses
            async with AsyncSessionLocal() as session:
                for doc_info in documents:
                    await session.execute(
                        update(Document).where(Document.id == doc_info["id"]).values(status="completed")
                    )
                await session.commit()
        except Exception:
            import logging
            logging.getLogger("voiceflow.ingestion").exception("Background ingestion failed")

    asyncio.create_task(_background_ingest())

    return {"jobId": job_id, "documents": documents, "status": "processing"}


@router.post("/company")
async def ingest_company(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """
    Crawl and ingest a company website.
    Used during onboarding step 1 (company profile).
    """
    website_url = body.get("website_url") or body.get("websiteUrl")
    agent_id = body.get("agentId")
    max_pages = body.get("maxPages", 20)

    if not website_url:
        return JSONResponse({"error": "website_url is required"}, status_code=400)

    # Find or default to first agent
    if agent_id:
        result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
        agent = result.scalar_one_or_none()
    else:
        result = await db.execute(select(Agent).where(Agent.tenantId == auth.tenant_id).limit(1))
        agent = result.scalar_one_or_none()

    effective_agent_id = agent.id if agent else "knowledge_base"

    job_id = str(uuid.uuid4())

    async def _background():
        try:
            await ingest_company_website(
                website_url=website_url,
                tenant_id=auth.tenant_id,
                agent_id=effective_agent_id,
                job_id=job_id,
                max_pages=max_pages,
            )
        except Exception:
            import logging
            logging.getLogger("voiceflow.ingestion").exception("Company ingestion failed")

    asyncio.create_task(_background())

    return {"jobId": job_id, "status": "processing", "websiteUrl": website_url}


@router.get("/status/{job_id}")
async def ingestion_status(job_id: str):
    """Get ingestion job status from Redis."""
    return get_job_status(job_id)


@router.get("/jobs")
async def ingestion_jobs(agentId: str = Query(...), auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Agent).where(Agent.id == agentId, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)

    # Return documents as jobs
    result = await db.execute(
        select(Document).where(Document.agentId == agentId).order_by(Document.createdAt.desc()).limit(50)
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "url": d.url,
            "s3Path": d.s3Path,
            "status": d.status,
            "title": d.title,
            "createdAt": d.createdAt.isoformat() if d.createdAt else None,
        }
        for d in docs
    ]
