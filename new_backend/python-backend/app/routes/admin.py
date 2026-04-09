"""
/admin routes — mirrors Express src/routes/admin.ts
Pipeline management.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Pipeline, Agent

router = APIRouter()


@router.post("/pipelines")
async def create_pipeline(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    name = body.get("name")
    if not name:
        return JSONResponse({"error": "Pipeline name is required"}, status_code=400)

    pipeline = Pipeline(
        tenantId=auth.tenant_id,
        name=name,
        stages=body.get("stages", []),
    )
    db.add(pipeline)
    await db.flush()
    await db.commit()
    await db.refresh(pipeline)
    return JSONResponse(
        {
            "id": pipeline.id, "tenantId": pipeline.tenantId, "name": pipeline.name,
            "stages": pipeline.stages, "status": pipeline.status,
            "createdAt": pipeline.createdAt.isoformat() if pipeline.createdAt else None,
        },
        status_code=201,
    )


@router.get("/pipelines")
async def list_pipelines(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.tenantId == auth.tenant_id).order_by(Pipeline.createdAt.desc()))
    pipelines = result.scalars().all()
    return {
        "pipelines": [
            {
                "id": p.id, "tenantId": p.tenantId, "name": p.name,
                "stages": p.stages, "status": p.status,
                "lastRunAt": p.lastRunAt.isoformat() if p.lastRunAt else None,
                "createdAt": p.createdAt.isoformat() if p.createdAt else None,
            }
            for p in pipelines
        ]
    }


@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(pipeline_id: str, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenantId == auth.tenant_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    if "name" in body:
        pipeline.name = body["name"]
    if "stages" in body:
        pipeline.stages = body["stages"]
    await db.commit()
    await db.refresh(pipeline)
    return {
        "id": pipeline.id, "name": pipeline.name, "stages": pipeline.stages,
        "status": pipeline.status,
    }


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenantId == auth.tenant_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    await db.delete(pipeline)
    await db.commit()
    return {"success": True}


@router.post("/pipelines/trigger")
async def trigger_pipeline(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    pipeline_id = body.get("pipeline_id")
    if not pipeline_id:
        return JSONResponse({"error": "pipeline_id is required"}, status_code=400)

    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenantId == auth.tenant_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    from datetime import datetime, timezone
    pipeline.status = "running"
    pipeline.lastRunAt = datetime.now(timezone.utc)
    await db.commit()

    # Simulate completion
    pipeline.status = "completed"
    await db.commit()

    return {"status": "triggered", "pipeline_id": pipeline_id}


@router.get("/pipeline_agents")
async def list_pipeline_agents(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.tenantId == auth.tenant_id).order_by(Agent.createdAt.desc())
    )
    agents = result.scalars().all()
    return {
        "pipeline_agents": [
            {
                "id": a.id, "name": a.name, "agent_type": a.voiceType or "general",
                "agent_id": a.id, "status": a.status,
            }
            for a in agents
        ]
    }


@router.post("/pipeline_agents")
async def create_pipeline_agent(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    agent_id = body.get("agent_id")
    if agent_id:
        result = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenantId == auth.tenant_id))
        agent = result.scalar_one_or_none()
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return {"id": agent.id, "name": body.get("name", agent.name), "agent_type": body.get("agent_type"), "agent_id": agent.id}
    return JSONResponse({"error": "agent_id required"}, status_code=400)
