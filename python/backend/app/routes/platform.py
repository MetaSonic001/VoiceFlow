"""
/api/audit, /api/notifications, /api/system routes.
Real dynamic data for dashboard pages + audit logging utility.
"""
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.auth import AuthContext, get_auth
from app.models import AuditLog, Notification

logger = logging.getLogger("voiceflow.platform")
router = APIRouter()

_start_time = time.time()


# ═══════════════════════════════════════════════════════════════════════════════
# Audit Logging
# ═══════════════════════════════════════════════════════════════════════════════

async def record_audit(
    tenant_id: str,
    user_id: str | None,
    action: str,
    resource: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
):
    """Fire-and-forget audit log entry. Call from any route."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(AuditLog(
                tenantId=tenant_id,
                userId=user_id,
                action=action,
                resource=resource,
                resourceId=resource_id,
                details=details,
                ipAddress=ip_address,
            ))
            await db.commit()
    except Exception:
        logger.exception("Failed to write audit log")


async def create_notification(
    tenant_id: str,
    title: str,
    message: str,
    notif_type: str = "info",
    user_id: str | None = None,
    link: str | None = None,
):
    """Create a notification for a tenant/user."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(Notification(
                tenantId=tenant_id,
                userId=user_id,
                type=notif_type,
                title=title,
                message=message,
                link=link,
            ))
            await db.commit()
    except Exception:
        logger.exception("Failed to create notification")


# ═══════════════════════════════════════════════════════════════════════════════
# Audit Log Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/audit")
async def get_audit_logs(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.tenantId == auth.tenant_id)
        .order_by(desc(AuditLog.createdAt))
        .offset(offset)
        .limit(min(limit, 200))
    )
    logs = result.scalars().all()

    count_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.tenantId == auth.tenant_id)
    )
    total = count_result.scalar() or 0

    return {
        "logs": [
            {
                "id": l.id,
                "userId": l.userId,
                "action": l.action,
                "resource": l.resource,
                "resourceId": l.resourceId,
                "details": l.details,
                "ipAddress": l.ipAddress,
                "createdAt": l.createdAt.isoformat() if l.createdAt else None,
            }
            for l in logs
        ],
        "total": total,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Notification Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/notifications")
async def get_notifications(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
    unread_only: bool = False,
):
    query = select(Notification).where(Notification.tenantId == auth.tenant_id)
    if unread_only:
        query = query.where(Notification.isRead == False)  # noqa: E712
    query = query.order_by(desc(Notification.createdAt)).limit(50)

    result = await db.execute(query)
    notifs = result.scalars().all()

    unread_count_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.tenantId == auth.tenant_id,
            Notification.isRead == False,  # noqa: E712
        )
    )
    unread_count = unread_count_result.scalar() or 0

    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "isRead": n.isRead,
                "link": n.link,
                "createdAt": n.createdAt.isoformat() if n.createdAt else None,
            }
            for n in notifs
        ],
        "unreadCount": unread_count,
    }


@router.post("/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.tenantId == auth.tenant_id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return JSONResponse({"error": "Notification not found"}, status_code=404)
    notif.isRead = True
    await db.commit()
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_read(
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import update
    await db.execute(
        update(Notification)
        .where(Notification.tenantId == auth.tenant_id, Notification.isRead == False)  # noqa: E712
        .values(isRead=True)
    )
    await db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# System Health Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/system/health")
async def system_health(auth: AuthContext = Depends(get_auth)):
    """Real system health: CPU, memory, disk via psutil + service connectivity checks."""
    import psutil

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Service checks
    services = {}

    # PostgreSQL
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
        services["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        services["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis
    try:
        import redis.asyncio as aioredis
        from app.config import settings as _s
        r = aioredis.Redis(host=_s.REDIS_HOST, port=_s.REDIS_PORT, socket_timeout=2)
        start = time.time()
        await r.ping()
        latency = int((time.time() - start) * 1000)
        await r.aclose()
        services["redis"] = {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # ChromaDB
    try:
        import httpx
        from app.config import settings as _s
        async with httpx.AsyncClient(timeout=3) as client:
            start = time.time()
            resp = await client.get(f"http://{_s.CHROMA_HOST}:{_s.CHROMA_PORT}/api/v2/heartbeat")
            latency = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                services["chromadb"] = {"status": "healthy", "latency_ms": latency}
            else:
                services["chromadb"] = {"status": "degraded", "http_status": resp.status_code}
    except Exception as e:
        services["chromadb"] = {"status": "unhealthy", "error": str(e)}

    # MinIO
    try:
        import httpx
        from app.config import settings as _s
        minio_ep = _s.MINIO_ENDPOINT or "localhost:9020"
        async with httpx.AsyncClient(timeout=3) as client:
            start = time.time()
            resp = await client.get(f"http://{minio_ep}/minio/health/live")
            latency = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                services["minio"] = {"status": "healthy", "latency_ms": latency}
            else:
                services["minio"] = {"status": "degraded", "http_status": resp.status_code}
    except Exception as e:
        services["minio"] = {"status": "unhealthy", "error": str(e)}

    uptime = int(time.time() - _start_time)

    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "memory_used_gb": round(mem.used / (1024 ** 3), 2),
            "memory_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        },
        "services": services,
        "uptime_seconds": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
