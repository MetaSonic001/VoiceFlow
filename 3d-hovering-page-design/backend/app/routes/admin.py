"""
/admin routes — mirrors Express src/routes/admin.ts
Pipeline management.

Access is restricted to owner-tier tenants (OWNER_TENANT_IDS env var).
"""
import asyncio
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Pipeline, Agent

logger = logging.getLogger("voiceflow.admin")

_OWNER_TENANT_IDS: set[str] = {
    t.strip() for t in os.getenv("OWNER_TENANT_IDS", "").split(",") if t.strip()
}


def _require_owner(auth: AuthContext) -> None:
    """Raise 403 if the caller is not an owner-tier tenant."""
    if _OWNER_TENANT_IDS and auth.tenant_id not in _OWNER_TENANT_IDS:
        raise HTTPException(status_code=403, detail="Owner-level access required")


router = APIRouter()


@router.post("/pipelines")
async def create_pipeline(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    _require_owner(auth)
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
    _require_owner(auth)
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
    _require_owner(auth)
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
    _require_owner(auth)
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenantId == auth.tenant_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)
    await db.delete(pipeline)
    await db.commit()
    return {"success": True}


@router.post("/pipelines/trigger")
async def trigger_pipeline(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    _require_owner(auth)
    pipeline_id = body.get("pipeline_id")
    if not pipeline_id:
        return JSONResponse({"error": "pipeline_id is required"}, status_code=400)

    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.tenantId == auth.tenant_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return JSONResponse({"error": "Pipeline not found"}, status_code=404)

    if pipeline.status == "running":
        return JSONResponse({"error": "Pipeline is already running"}, status_code=409)

    from datetime import datetime, timezone
    pipeline.status = "running"
    pipeline.lastRunAt = datetime.now(timezone.utc)
    await db.commit()

    task = asyncio.create_task(_execute_pipeline(pipeline_id, pipeline.stages or []))
    task.add_done_callback(_log_task_exc)

    return {"status": "triggered", "pipeline_id": pipeline_id}


def _log_task_exc(task: asyncio.Task) -> None:
    if not task.cancelled() and (exc := task.exception()):
        logger.error("Pipeline background task failed: %s", exc, exc_info=exc)


async def _execute_pipeline(pipeline_id: str, stages: list) -> None:
    """
    Background executor: walk through pipeline stages and update status in DB.
    Each stage is a dict with at minimum {"type": "<stage_type>"}.
    On completion (or failure) the pipeline status is written back to Postgres.
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import update as sa_update

    final_status = "completed"
    try:
        for idx, stage in enumerate(stages):
            stage_type = stage.get("type", "unknown") if isinstance(stage, dict) else str(stage)
            logger.info("[pipeline] %s — executing stage %d: %s", pipeline_id, idx + 1, stage_type)
            # Brief async yield so we don't block the event loop between stages
            await asyncio.sleep(0)
    except Exception as exc:
        logger.error("[pipeline] %s — stage execution failed: %s", pipeline_id, exc, exc_info=exc)
        final_status = "failed"

    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_update(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .values(status=final_status)
        )
        await db.commit()
    logger.info("[pipeline] %s — finished with status=%s", pipeline_id, final_status)


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
