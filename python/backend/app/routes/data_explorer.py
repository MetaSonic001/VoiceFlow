"""
/api/data-explorer — Visualise what's stored in Postgres, Redis, ChromaDB.
Gives a complete picture of the system's data state.
"""
import json
import logging
import os

import chromadb
import redis
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthContext, get_auth
from app.database import get_db
from app.models import Tenant, User, Agent, Document, CallLog, RetrainingExample, Brand

router = APIRouter()
logger = logging.getLogger("voiceflow.data_explorer")


@router.get("/overview")
async def data_overview(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """High-level counts from all three stores."""
    # Postgres counts
    pg = {}
    for model, name in [
        (Tenant, "tenants"), (User, "users"), (Agent, "agents"),
        (Document, "documents"), (CallLog, "call_logs"),
        (RetrainingExample, "retraining_examples"), (Brand, "brands"),
    ]:
        r = await db.execute(select(func.count()).select_from(model))
        pg[name] = r.scalar() or 0

    # ChromaDB
    chroma = {"collections": 0, "total_chunks": 0, "details": []}
    try:
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8030"))
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
        collections = client.list_collections()
        chroma["collections"] = len(collections)
        for col in collections:
            count = col.count()
            chroma["total_chunks"] += count
            chroma["details"].append({"name": col.name, "chunks": count})
    except Exception as e:
        chroma["error"] = str(e)

    # Redis
    redis_info = {"keys": 0, "bm25_indexes": 0, "jobs": 0, "conversations": 0}
    try:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "8020"))
        r = redis.Redis(host=host, port=port, decode_responses=True)
        r.ping()
        redis_info["keys"] = r.dbsize()
        for key in r.scan_iter("bm25:*", count=100):
            redis_info["bm25_indexes"] += 1
        for key in r.scan_iter("job:*", count=100):
            redis_info["jobs"] += 1
        for key in r.scan_iter("conversation:*", count=100):
            redis_info["conversations"] += 1
    except Exception as e:
        redis_info["error"] = str(e)

    return {"postgres": pg, "chromadb": chroma, "redis": redis_info}


@router.get("/postgres")
async def postgres_detail(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """Detailed Postgres data for the tenant."""
    tid = auth.tenant_id

    # Tenant info
    t = await db.execute(select(Tenant).where(Tenant.id == tid))
    tenant = t.scalar_one_or_none()
    tenant_data = None
    if tenant:
        tenant_data = {
            "id": tenant.id, "name": tenant.name, "domain": tenant.domain,
            "settings": tenant.settings, "isActive": tenant.isActive,
            "createdAt": str(tenant.createdAt),
        }

    # Agents
    agents = []
    result = await db.execute(select(Agent).where(Agent.tenantId == tid).order_by(Agent.createdAt.desc()))
    for a in result.scalars().all():
        agents.append({
            "id": a.id, "name": a.name, "status": a.status,
            "voiceType": a.voiceType, "totalCalls": a.totalCalls,
            "totalChats": a.totalChats, "createdAt": str(a.createdAt),
        })

    # Documents
    docs = []
    result = await db.execute(select(Document).where(Document.tenantId == tid).order_by(Document.createdAt.desc()))
    for d in result.scalars().all():
        docs.append({
            "id": d.id, "status": d.status, "title": d.title, "url": d.url,
            "s3Path": d.s3Path, "agentId": d.agentId, "createdAt": str(d.createdAt),
        })

    # Users
    users = []
    result = await db.execute(select(User).where(User.tenantId == tid))
    for u in result.scalars().all():
        users.append({"id": u.id, "email": u.email, "name": u.name, "role": u.role})

    # Call logs (last 20)
    logs = []
    result = await db.execute(
        select(CallLog).where(CallLog.tenantId == tid).order_by(CallLog.createdAt.desc()).limit(20)
    )
    for log in result.scalars().all():
        logs.append({
            "id": log.id, "agentId": log.agentId, "callerPhone": log.callerPhone,
            "durationSeconds": log.durationSeconds,
            "flaggedForRetraining": log.flaggedForRetraining,
            "createdAt": str(log.createdAt),
        })

    return {
        "tenant": tenant_data, "agents": agents,
        "documents": docs, "users": users, "callLogs": logs,
    }


@router.get("/chromadb")
async def chromadb_detail(auth: AuthContext = Depends(get_auth)):
    """Detailed ChromaDB data — collections, sample chunks, metadata."""
    try:
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", "8030"))
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()
    except Exception as e:
        return {"error": f"ChromaDB unavailable: {e}"}

    collections_data = []
    for col in client.list_collections():
        col_info = {"name": col.name, "count": col.count(), "samples": []}
        try:
            # Get a sample of chunks
            data = col.peek(limit=10)
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            ids = data.get("ids", [])
            for i in range(len(ids)):
                col_info["samples"].append({
                    "id": ids[i],
                    "text": docs[i][:200] + "..." if len(docs[i]) > 200 else docs[i],
                    "metadata": metas[i] if i < len(metas) else {},
                })
        except Exception:
            pass
        collections_data.append(col_info)

    return {"collections": collections_data}


@router.get("/redis")
async def redis_detail(auth: AuthContext = Depends(get_auth)):
    """Detailed Redis data — job statuses, BM25 indexes, conversation keys."""
    try:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "8020"))
        r = redis.Redis(host=host, port=port, decode_responses=True)
        r.ping()
    except Exception as e:
        return {"error": f"Redis unavailable: {e}"}

    result = {"jobs": [], "bm25_indexes": [], "conversations": [], "other_keys": []}

    for key in r.scan_iter("*", count=500):
        ttl = r.ttl(key)
        if key.startswith("job:"):
            try:
                data = json.loads(r.get(key) or "{}")
                result["jobs"].append({"key": key, "ttl": ttl, **data})
            except Exception:
                result["jobs"].append({"key": key, "ttl": ttl})
        elif key.startswith("bm25:"):
            try:
                data = json.loads(r.get(key) or "{}")
                result["bm25_indexes"].append({
                    "key": key, "ttl": ttl,
                    "doc_count": len(data.get("documents", [])),
                })
            except Exception:
                result["bm25_indexes"].append({"key": key, "ttl": ttl})
        elif key.startswith("conversation:"):
            result["conversations"].append({"key": key, "ttl": ttl})
        else:
            result["other_keys"].append({"key": key, "ttl": ttl, "type": r.type(key)})

    return result
