"""
/auth routes — mirrors Express src/routes/auth.ts
POST /clerk_sync, /login, /signup
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt as pyjwt

from fastapi.responses import JSONResponse

from app.database import get_db
from app.models import User, Tenant, Brand
from app.config import settings
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class EmailBody(BaseModel):
    email: str


def _make_token(user_id: str, tenant_id: str, email: str) -> str:
    payload = {
        "userId": user_id,
        "tenantId": tenant_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def _user_response(user: User, tenant: Optional[Tenant], brand: Optional[Brand]) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "tenantId": user.tenantId,
        "brandId": user.brandId,
        "tenant": {"id": tenant.id, "name": tenant.name} if tenant else None,
        "brand": {"id": brand.id, "name": brand.name} if brand else None,
    }


@router.post("/clerk_sync")
async def clerk_sync(body: EmailBody, db: AsyncSession = Depends(get_db)):
    email = body.email
    if not email:
        return JSONResponse({"error": "Email is required"}, status_code=400)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    tenant = None
    brand = None

    if not user:
        tenant = Tenant(name=f"{email.split('@')[0]}'s Organization")
        db.add(tenant)
        await db.flush()

        brand = Brand(tenantId=tenant.id, name="Default Brand")
        db.add(brand)
        await db.flush()

        user = User(email=email, tenantId=tenant.id, brandId=brand.id)
        db.add(user)
        await db.flush()
        await db.commit()
    else:
        r = await db.execute(select(Tenant).where(Tenant.id == user.tenantId))
        tenant = r.scalar_one_or_none()
        if user.brandId:
            r2 = await db.execute(select(Brand).where(Brand.id == user.brandId))
            brand = r2.scalar_one_or_none()

    token = _make_token(user.id, user.tenantId, user.email)
    return {
        "access_token": token,
        "user": _user_response(user, tenant, brand),
    }


@router.post("/login")
async def login(body: EmailBody, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    r = await db.execute(select(Tenant).where(Tenant.id == user.tenantId))
    tenant = r.scalar_one_or_none()
    brand = None
    if user.brandId:
        r2 = await db.execute(select(Brand).where(Brand.id == user.brandId))
        brand = r2.scalar_one_or_none()

    token = _make_token(user.id, user.tenantId, user.email)
    return {
        "access_token": token,
        "user": _user_response(user, tenant, brand),
    }


@router.post("/signup")
async def signup(body: EmailBody, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        return JSONResponse({"error": "User already exists"}, status_code=400)

    tenant = Tenant(name=f"{body.email.split('@')[0]}'s Organization")
    db.add(tenant)
    await db.flush()

    brand = Brand(tenantId=tenant.id, name="Default Brand")
    db.add(brand)
    await db.flush()

    user = User(email=body.email, tenantId=tenant.id, brandId=brand.id)
    db.add(user)
    await db.flush()
    await db.commit()

    token = _make_token(user.id, tenant.id, user.email)
    return {
        "access_token": token,
        "user": _user_response(user, tenant, brand),
    }
