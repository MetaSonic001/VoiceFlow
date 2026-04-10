"""
/api/templates routes — mirrors Express src/routes/templates.ts
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import AgentTemplate

router = APIRouter()


def _template_dict(t: AgentTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "persona": t.baseSystemPrompt,
        "baseSystemPrompt": t.baseSystemPrompt,
        "defaultCapabilities": t.defaultCapabilities,
        "suggestedKnowledgeCategories": t.suggestedKnowledgeCategories,
        "defaultTools": t.defaultTools,
        "icon": t.icon,
        "isActive": t.isActive,
        "createdAt": t.createdAt.isoformat() if t.createdAt else None,
        "updatedAt": t.updatedAt.isoformat() if t.updatedAt else None,
    }


@router.get("/")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTemplate)
        .where(AgentTemplate.isActive.is_(True))
        .order_by(AgentTemplate.name)
    )
    templates = result.scalars().all()
    return {"templates": [_template_dict(t) for t in templates]}


@router.get("/{template_id}")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    return _template_dict(t)


@router.post("/")
async def create_template(
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agent template (admin)."""
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "name is required"}, status_code=400)

    existing = await db.execute(select(AgentTemplate).where(AgentTemplate.name == name))
    if existing.scalar_one_or_none():
        return JSONResponse({"error": "Template name already exists"}, status_code=409)

    t = AgentTemplate(
        name=name,
        description=body.get("description", ""),
        baseSystemPrompt=body.get("baseSystemPrompt", ""),
        defaultCapabilities=body.get("defaultCapabilities", []),
        suggestedKnowledgeCategories=body.get("suggestedKnowledgeCategories", []),
        defaultTools=body.get("defaultTools", []),
        icon=body.get("icon", "Bot"),
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return JSONResponse(_template_dict(t), status_code=201)


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    body: dict,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing agent template."""
    result = await db.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        return JSONResponse({"error": "Template not found"}, status_code=404)

    for field in ("name", "description", "baseSystemPrompt", "icon"):
        if field in body:
            setattr(t, field, body[field])
    for field in ("defaultCapabilities", "suggestedKnowledgeCategories", "defaultTools"):
        if field in body:
            setattr(t, field, body[field])
    if "isActive" in body:
        t.isActive = bool(body["isActive"])

    await db.commit()
    await db.refresh(t)
    return _template_dict(t)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete (deactivate) a template."""
    result = await db.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    t.isActive = False
    await db.commit()
    return {"deleted": True, "id": template_id}
