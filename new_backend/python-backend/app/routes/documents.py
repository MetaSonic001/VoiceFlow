"""
/api/documents routes — mirrors Express src/routes/documents.ts
"""
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Document, Agent
from app.config import settings

router = APIRouter()


def _doc_to_dict(doc: Document) -> dict:
    return {
        "id": doc.id,
        "url": doc.url,
        "s3Path": doc.s3Path,
        "status": doc.status,
        "title": doc.title,
        "content": doc.content,
        "metadata": doc.metadata_,
        "tenantId": doc.tenantId,
        "agentId": doc.agentId,
        "createdAt": doc.createdAt.isoformat() if doc.createdAt else None,
        "updatedAt": doc.updatedAt.isoformat() if doc.updatedAt else None,
    }


@router.get("/")
async def list_documents(agentId: str = Query(...), auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Agent).where(Agent.id == agentId, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)

    result = await db.execute(select(Document).where(Document.agentId == agentId).order_by(Document.createdAt.desc()))
    docs = result.scalars().all()
    return [_doc_to_dict(d) for d in docs]


@router.get("/{doc_id}")
async def get_document(doc_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    return _doc_to_dict(doc)


@router.post("/")
async def create_document(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    agent_id = body.get("agentId")
    url = body.get("url")
    if not agent_id:
        return JSONResponse({"error": "\"agentId\" is required"}, status_code=400)

    r = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    if not r.scalar_one_or_none():
        return JSONResponse({"error": "Access denied"}, status_code=403)

    doc = Document(url=url, agentId=agent_id, tenantId=auth.tenant_id, status="pending")
    db.add(doc)
    await db.flush()
    await db.commit()
    await db.refresh(doc)

    # Trigger ingestion
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{settings.FASTAPI_URL}/ingest",
                json={"tenantId": auth.tenant_id, "agentId": agent_id, "urls": [url] if url else []},
            )
    except Exception:
        pass

    return JSONResponse(_doc_to_dict(doc), status_code=201)


@router.put("/{doc_id}")
async def update_document(doc_id: str, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)

    for field in ("status", "title", "content"):
        if field in body:
            setattr(doc, field, body[field])
    if "metadata" in body:
        doc.metadata_ = body["metadata"]
    await db.commit()
    await db.refresh(doc)
    return _doc_to_dict(doc)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id, Document.tenantId == auth.tenant_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return JSONResponse({"error": "Document not found"}, status_code=404)
    await db.delete(doc)
    await db.commit()
    return Response(status_code=204)
