"""
/auth routes — mirrors Express src/routes/auth.ts
POST /clerk_sync, /login, /signup
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt as pyjwt
import bcrypt

from fastapi.responses import JSONResponse

from app.database import get_db
from app.models import User, Tenant, Brand
from app.config import settings
from pydantic import BaseModel
from typing import Optional

# Compatibility: some route modules import `require_agent_access` and `AuthContext`
# from `app.routes.auth`. Re-export from the centralized `app.auth` module so
# older import locations remain valid.
from app.auth import get_auth as require_agent_access, AuthContext

router = APIRouter()


class EmailBody(BaseModel):
    email: str


class LoginBody(BaseModel):
    email: str
    password: str


class SignupBody(BaseModel):
    email: str
    password: str


def _make_token(user_id: str, tenant_id: str, email: str) -> str:
    payload = {
        "sub": user_id,          # RFC 7519 subject claim
        "userId": user_id,       # kept for legacy SDK tokens already issued
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
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    # Reject if account has no password hash (e.g. created via clerk_sync before passwords were enabled)
    if not user.passwordHash:
        return JSONResponse({"error": "Account requires password setup"}, status_code=401)

    try:
        password_valid = bcrypt.checkpw(
            body.password.encode(), user.passwordHash.encode()
        )
    except Exception:
        password_valid = False

    if not password_valid:
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
async def signup(body: SignupBody, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        return JSONResponse({"error": "User already exists"}, status_code=400)

    if len(body.password) < 8:
        return JSONResponse({"error": "Password must be at least 8 characters"}, status_code=400)

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    tenant = Tenant(name=f"{body.email.split('@')[0]}'s Organization")
    db.add(tenant)
    await db.flush()

    brand = Brand(tenantId=tenant.id, name="Default Brand")
    db.add(brand)
    await db.flush()

    user = User(email=body.email, tenantId=tenant.id, brandId=brand.id, passwordHash=pw_hash)
    db.add(user)
    await db.flush()
    await db.commit()

    token = _make_token(user.id, tenant.id, user.email)
    return {
        "access_token": token,
        "user": _user_response(user, tenant, brand),
    }
