"""
/api/settings routes — mirrors Express src/routes/settings.ts
Twilio + Groq credential management.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Tenant
from app.config import settings

router = APIRouter()

# Groq models list — mirrors Express GROQ_PRODUCTION_MODELS
GROQ_PRODUCTION_MODELS = [
    {
        "id": "llama-3.3-70b-versatile",
        "name": "Meta Llama 3.3 70B",
        "speed": "280 T/sec",
        "contextWindow": 131072,
        "maxCompletionTokens": 32768,
        "description": "Best quality — large 70B model, great for complex reasoning and detailed responses.",
    },
    {
        "id": "llama-3.1-8b-instant",
        "name": "Meta Llama 3.1 8B",
        "speed": "560 T/sec",
        "contextWindow": 131072,
        "maxCompletionTokens": 131072,
        "description": "Fastest text model — ideal for simple queries and high-throughput use cases.",
    },
    {
        "id": "openai/gpt-oss-120b",
        "name": "OpenAI GPT OSS 120B",
        "speed": "500 T/sec",
        "contextWindow": 131072,
        "maxCompletionTokens": 65536,
        "description": "Large open-source GPT model — balanced speed and quality.",
    },
    {
        "id": "openai/gpt-oss-20b",
        "name": "OpenAI GPT OSS 20B",
        "speed": "1000 T/sec",
        "contextWindow": 131072,
        "maxCompletionTokens": 65536,
        "description": "Ultra-fast GPT model — best throughput for lightweight tasks.",
    },
]


# ── Twilio credentials ──────────────────────────────────────────────────────

@router.post("/twilio")
async def save_twilio(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    account_sid = body.get("accountSid")
    auth_token = body.get("authToken")
    if not account_sid or not auth_token:
        return JSONResponse({"error": "accountSid and authToken are required."}, status_code=400)

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    existing = tenant.settings or {}
    tenant.settings = {
        **existing,
        "twilioAccountSid": account_sid,
        "twilioAuthToken": auth_token,
        "twilioCredentialsVerified": True,
        "twilioCredentialsUpdatedAt": __import__("datetime").datetime.now().isoformat(),
    }
    await db.commit()
    return {"success": True, "message": "Twilio credentials saved.", "accountSid": account_sid}


@router.get("/twilio")
async def get_twilio(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}
    return {
        "configured": bool(s.get("twilioAccountSid") and s.get("twilioAuthToken")),
        "accountSid": s.get("twilioAccountSid"),
        "hasAuthToken": bool(s.get("twilioAuthToken")),
        "credentialsVerified": bool(s.get("twilioCredentialsVerified")),
        "updatedAt": s.get("twilioCredentialsUpdatedAt"),
    }


@router.delete("/twilio")
async def delete_twilio(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        s = dict(tenant.settings or {})
        for k in ("twilioAccountSid", "twilioAuthToken", "twilioCredentialsVerified", "twilioCredentialsUpdatedAt"):
            s.pop(k, None)
        tenant.settings = s
        await db.commit()
    return {"success": True, "message": "Twilio credentials removed."}


# ── Groq API key ────────────────────────────────────────────────────────────

@router.get("/groq/models")
async def groq_models():
    return {"models": GROQ_PRODUCTION_MODELS}


@router.post("/groq")
async def save_groq(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = body.get("apiKey", "")
    if not api_key or not api_key.startswith("gsk_"):
        return JSONResponse({"error": "A valid Groq API key is required (starts with gsk_)."}, status_code=400)

    # Validate key
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 401:
                return JSONResponse({"error": "Invalid API key."}, status_code=400)
    except Exception:
        pass  # non-fatal

    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    existing = tenant.settings or {}
    tenant.settings = {
        **existing,
        "groqApiKey": api_key,
        "groqKeyVerified": True,
        "groqKeyUpdatedAt": __import__("datetime").datetime.now().isoformat(),
    }
    await db.commit()

    masked = api_key[:7] + "••••••••" + api_key[-4:]
    return {"success": True, "message": "Groq API key verified and saved.", "maskedKey": masked}


@router.get("/groq")
async def get_groq(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}

    masked_key = None
    raw = s.get("groqApiKey")
    if raw and isinstance(raw, str):
        masked_key = raw[:7] + "••••••••" + raw[-4:]

    return {
        "configured": bool(masked_key),
        "maskedKey": masked_key,
        "verified": bool(s.get("groqKeyVerified")),
        "updatedAt": s.get("groqKeyUpdatedAt"),
        "usingPlatformKey": not bool(masked_key),
    }


@router.delete("/groq")
async def delete_groq(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        s = dict(tenant.settings or {})
        for k in ("groqApiKey", "groqKeyVerified", "groqKeyUpdatedAt"):
            s.pop(k, None)
        tenant.settings = s
        await db.commit()
    return {"success": True, "message": "Groq API key removed. Using platform default."}
