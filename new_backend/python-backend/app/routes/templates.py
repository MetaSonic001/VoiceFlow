"""
/api/templates routes — mirrors Express src/routes/templates.ts
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AgentTemplate

router = APIRouter()


@router.get("/")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTemplate)
        .where(AgentTemplate.isActive.is_(True))
        .order_by(AgentTemplate.name)
    )
    templates = result.scalars().all()
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "defaultCapabilities": t.defaultCapabilities,
                "suggestedKnowledgeCategories": t.suggestedKnowledgeCategories,
                "defaultTools": t.defaultTools,
                "icon": t.icon,
            }
            for t in templates
        ]
    }


@router.get("/{template_id}")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    t = result.scalar_one_or_none()
    if not t:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "baseSystemPrompt": t.baseSystemPrompt,
        "defaultCapabilities": t.defaultCapabilities,
        "suggestedKnowledgeCategories": t.suggestedKnowledgeCategories,
        "defaultTools": t.defaultTools,
        "icon": t.icon,
        "isActive": t.isActive,
        "createdAt": t.createdAt.isoformat() if t.createdAt else None,
        "updatedAt": t.updatedAt.isoformat() if t.updatedAt else None,
    }
