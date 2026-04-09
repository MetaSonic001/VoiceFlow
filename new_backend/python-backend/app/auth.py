"""
Demo-mode auth dependency — mirrors the passthrough clerkAuth.ts middleware.
Reads x-tenant-id / x-user-id from headers, falls back to demo values.
"""
from fastapi import Request

DEMO_TENANT = "demo-tenant"
DEMO_USER = "demo-user"


class AuthContext:
    """Attached to every request — same as req.tenantId / req.userId in Express."""
    __slots__ = ("tenant_id", "user_id")

    def __init__(self, tenant_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.user_id = user_id


def get_auth(request: Request) -> AuthContext:
    tenant_id = request.headers.get("x-tenant-id", DEMO_TENANT)
    user_id = request.headers.get("x-user-id", DEMO_USER)
    return AuthContext(tenant_id=tenant_id, user_id=user_id)
