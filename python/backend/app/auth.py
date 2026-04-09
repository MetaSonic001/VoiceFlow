"""
Demo-mode auth dependency — mirrors the passthrough clerkAuth.ts middleware.
Reads x-tenant-id / x-user-id from headers, falls back to demo values.

Django registers users in django_users with tenant_id tenant-{uuid}; this app
also needs rows in SQLAlchemy tenants + users for FK constraints on agents.
"""
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Tenant, User

DEMO_TENANT = "demo-tenant"
DEMO_USER = "demo-user"


class AuthContext:
    """Attached to every request — same as req.tenantId / req.userId in Express."""
    __slots__ = ("tenant_id", "user_id")

    def __init__(self, tenant_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_id = user_id


def _parse_auth_headers(request: Request) -> AuthContext:
    # Empty header values must fall back (Django may send x-user-id: "")
    tenant_id = (request.headers.get("x-tenant-id") or "").strip() or DEMO_TENANT
    user_id = (request.headers.get("x-user-id") or "").strip() or DEMO_USER
    return AuthContext(tenant_id=tenant_id, user_id=user_id)


async def _ensure_tenant_and_user(
    db: AsyncSession,
    auth: AuthContext,
    email: Optional[str],
    display_name: Optional[str],
) -> None:
    tid, uid = auth.tenant_id, auth.user_id
    if not tid or not uid:
        return
    if tid == DEMO_TENANT and uid == DEMO_USER:
        return

    org_name = (display_name or "").strip() or (email.split("@", 1)[0] if email and "@" in email else "Organization")
    org_name = org_name[:255] or "Organization"

    for attempt in range(2):
        try:
            tr = await db.execute(select(Tenant).where(Tenant.id == tid))
            if not tr.scalar_one_or_none():
                db.add(Tenant(id=tid, name=org_name))
                await db.flush()

            ur = await db.execute(select(User).where(User.id == uid))
            if not ur.scalar_one_or_none():
                em = (email or "").strip() or f"{uid}@users.voiceflow.local"
                db.add(
                    User(
                        id=uid,
                        email=em[:254],
                        name=(display_name or "").strip() or None,
                        tenantId=tid,
                    )
                )
                await db.flush()

            await db.commit()
            return
        except IntegrityError:
            await db.rollback()
            if attempt == 1:
                raise


async def get_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    auth = _parse_auth_headers(request)
    email = (request.headers.get("x-user-email") or "").strip() or None
    name = (request.headers.get("x-user-name") or "").strip() or None
    await _ensure_tenant_and_user(db, auth, email=email, display_name=name)
    return auth
