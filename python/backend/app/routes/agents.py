"""
/api/agents routes — mirrors Express src/routes/agents.ts
GET /, GET /:id, POST /, PUT /:id, DELETE /:id
"""
from fastapi import APIRouter, Depends, Query, Response
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
        systemPrompt=request_data.get("systemPrompt", ""),
        voiceType=request_data.get("voiceType", "female"),
        llmPreferences=request_data.get("llmPreferences", {"model": "llama-3.3-70b-versatile"}),
        tokenLimit=request_data.get("tokenLimit", 4096),
        contextWindowStrategy=request_data.get("contextWindowStrategy", "condense"),
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

    for field in ("name", "systemPrompt", "voiceType", "llmPreferences", "tokenLimit", "contextWindowStrategy"):
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


@router.post("/{agent_id}/activate")
async def activate_agent(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    agent.status = "active"
    await db.commit()
    return {"success": True}


@router.post("/{agent_id}/pause")
async def pause_agent(agent_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    agent.status = "paused"
    await db.commit()
    return {"success": True}
