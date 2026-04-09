"""
/api/brands routes — mirrors Express src/routes/brands.ts
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Brand, Agent

router = APIRouter()


def _brand_dict(b: Brand, agent_count: int = 0) -> dict:
    return {
        "id": b.id,
        "tenantId": b.tenantId,
        "name": b.name,
        "brandVoice": b.brandVoice,
        "allowedTopics": b.allowedTopics,
        "restrictedTopics": b.restrictedTopics,
        "policyRules": b.policyRules,
        "createdAt": b.createdAt.isoformat() if b.createdAt else None,
        "updatedAt": b.updatedAt.isoformat() if b.updatedAt else None,
        "_count": {"agents": agent_count},
    }


@router.get("/")
async def list_brands(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.tenantId == auth.tenant_id).order_by(Brand.createdAt.desc()))
    brands = result.scalars().all()

    brand_ids = [b.id for b in brands]
    counts: dict[str, int] = {}
    if brand_ids:
        cr = await db.execute(
            select(Agent.brandId, func.count(Agent.id)).where(Agent.brandId.in_(brand_ids)).group_by(Agent.brandId)
        )
        counts = dict(cr.all())

    return [_brand_dict(b, counts.get(b.id, 0)) for b in brands]


@router.get("/{brand_id}")
async def get_brand(brand_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id, Brand.tenantId == auth.tenant_id))
    brand = result.scalar_one_or_none()
    if not brand:
        return JSONResponse({"error": "Brand not found"}, status_code=404)

    agents_r = await db.execute(
        select(Agent.id, Agent.name, Agent.status).where(Agent.brandId == brand_id)
    )
    agents = [{"id": r[0], "name": r[1], "status": r[2]} for r in agents_r.all()]

    d = _brand_dict(brand)
    d["agents"] = agents
    return d


@router.post("/")
async def create_brand(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    name = body.get("name")
    if not name:
        return JSONResponse({"error": "\"name\" is required"}, status_code=400)

    brand = Brand(
        tenantId=auth.tenant_id,
        name=name,
        brandVoice=body.get("brandVoice"),
        allowedTopics=body.get("allowedTopics", []),
        restrictedTopics=body.get("restrictedTopics", []),
        policyRules=body.get("policyRules", []),
    )
    db.add(brand)
    await db.flush()
    await db.commit()
    await db.refresh(brand)
    return JSONResponse(_brand_dict(brand), status_code=201)


@router.put("/{brand_id}")
async def update_brand(brand_id: str, body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id, Brand.tenantId == auth.tenant_id))
    brand = result.scalar_one_or_none()
    if not brand:
        return JSONResponse({"error": "Brand not found"}, status_code=404)

    for field in ("name", "brandVoice", "allowedTopics", "restrictedTopics", "policyRules"):
        if field in body:
            setattr(brand, field, body[field])
    await db.commit()
    await db.refresh(brand)
    return _brand_dict(brand)


@router.delete("/{brand_id}")
async def delete_brand(brand_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.id == brand_id, Brand.tenantId == auth.tenant_id))
    brand = result.scalar_one_or_none()
    if not brand:
        return JSONResponse({"error": "Brand not found"}, status_code=404)
    await db.delete(brand)
    await db.commit()
    return {"deleted": True}
