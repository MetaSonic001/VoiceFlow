"""
Auth dependencies for VoiceFlow FastAPI backend.

Two auth modes are supported:
1.  Header passthrough (get_auth) — reads x-tenant-id / x-user-id headers forwarded
    by the Django frontend proxy.  Used by most protected routes.
2.  JWT bearer (get_current_user) — validates a HS256 JWT in the Authorization header.
    Used by routes that need token-based auth (e.g. WebSocket endpoints).

Django registers users in django_users with tenant_id tenant-{uuid}; this app
also needs rows in SQLAlchemy tenants + users for FK constraints on agents.
"""
from typing import Optional

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Tenant, User

DEMO_TENANT = "demo-tenant"
DEMO_USER = "demo-user"

_bearer_scheme = HTTPBearer(auto_error=False)


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


# ── JWT bearer authentication ─────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Validate a HS256 JWT Bearer token and return an AuthContext.

    Token payload must contain:
      - sub        : user ID
      - tenant_id  : tenant ID

    Raises HTTP 401 if the token is missing, expired, or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tenant_id: str = payload.get("tenant_id") or payload.get("tenantId") or DEMO_TENANT
    user_id: str = payload.get("sub") or DEMO_USER
    auth = AuthContext(tenant_id=tenant_id, user_id=user_id)

    email: Optional[str] = payload.get("email")
    name: Optional[str] = payload.get("name")
    await _ensure_tenant_and_user(db, auth, email=email, display_name=name)
    return auth

