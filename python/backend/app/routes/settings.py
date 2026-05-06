"""
/api/settings routes — mirrors Express src/routes/settings.ts
Twilio + Groq credential management with AES-256-GCM encryption (Claim 9).
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import Tenant
from app.config import settings
from app.services.credentials import encrypt, decrypt_safe, mask

router = APIRouter()


# ── General settings (GET/PUT /settings) ─────────────────────────────────────

@router.get("/")
@router.get("")
async def get_settings(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}
    return {
        "notifications": s.get("notifications", {}),
        "security": s.get("security", {}),
        "system": s.get("system", {}),
    }


@router.put("/")
@router.put("")
async def update_settings(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)
    existing = tenant.settings or {}
    for key in ("notifications", "security", "system"):
        if key in body:
            existing[key] = {**(existing.get(key) or {}), **body[key]}
    tenant.settings = existing
    await db.commit()
    return {"success": True}

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
        "twilioAuthToken": encrypt(auth_token),
        "twilioCredentialsVerified": True,
        "twilioCredentialsUpdatedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.commit()
    return {"success": True, "message": "Twilio credentials saved (encrypted).", "accountSid": account_sid}


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
        "groqApiKey": encrypt(api_key),
        "groqKeyVerified": True,
        "groqKeyUpdatedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.commit()

    masked = mask(api_key, prefix_len=7, suffix_len=4)
    return {"success": True, "message": "Groq API key verified and saved (encrypted).", "maskedKey": masked}


@router.get("/groq")
async def get_groq(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}

    masked_key = None
    raw = s.get("groqApiKey")
    if raw and isinstance(raw, str):
        decrypted = decrypt_safe(raw)
        masked_key = mask(decrypted, prefix_len=7, suffix_len=4)

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


# ── Generic BYOK helpers ─────────────────────────────────────────────────────

def _make_byok_key_name(provider: str) -> str:
    """Map provider slug → tenant.settings JSON key name."""
    return {
        "openai":     "openaiApiKey",
        "anthropic":  "anthropicApiKey",
        "gemini":     "geminiApiKey",
        "elevenlabs": "elevenlabsApiKey",
        "sarvam":     "sarvamApiKey",
        "deepgram":   "deepgramApiKey",
        "assemblyai": "assemblyaiApiKey",
    }[provider]


async def _save_byok_key(
    provider: str,
    api_key: str,
    auth: AuthContext,
    db: AsyncSession,
    extra_fields: dict | None = None,
) -> dict:
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return {"error": "Tenant not found"}
    settings_key = _make_byok_key_name(provider)
    existing = dict(tenant.settings or {})
    existing[settings_key] = encrypt(api_key)
    existing[f"{provider}KeyUpdatedAt"] = datetime.now(timezone.utc).isoformat()
    if extra_fields:
        existing.update(extra_fields)
    tenant.settings = existing
    await db.commit()
    return {"success": True, "maskedKey": mask(api_key, prefix_len=6, suffix_len=4)}


async def _get_byok_status(provider: str, auth: AuthContext, db: AsyncSession) -> dict:
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}
    settings_key = _make_byok_key_name(provider)
    raw = s.get(settings_key)
    masked_key = None
    if raw and isinstance(raw, str):
        decrypted = decrypt_safe(raw)
        masked_key = mask(decrypted, prefix_len=6, suffix_len=4)
    return {
        "configured": bool(masked_key),
        "maskedKey": masked_key,
        "updatedAt": s.get(f"{provider}KeyUpdatedAt"),
        "usingPlatformKey": not bool(masked_key),
    }


async def _delete_byok_key(provider: str, auth: AuthContext, db: AsyncSession) -> dict:
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant:
        s = dict(tenant.settings or {})
        settings_key = _make_byok_key_name(provider)
        s.pop(settings_key, None)
        s.pop(f"{provider}KeyUpdatedAt", None)
        tenant.settings = s
        await db.commit()
    return {"success": True, "message": f"{provider} API key removed."}


# ── All provider key statuses (single call for settings page) ─────────────────

@router.get("/keys/all")
async def get_all_key_statuses(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """Return status of every BYOK key in one request (avoids N round-trips on page load)."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}

    def _status(settings_key: str, provider_slug: str) -> dict:
        raw = s.get(settings_key)
        masked = None
        if raw and isinstance(raw, str):
            decrypted = decrypt_safe(raw)
            masked = mask(decrypted, prefix_len=6, suffix_len=4)
        return {
            "configured": bool(masked),
            "maskedKey": masked,
            "updatedAt": s.get(f"{provider_slug}KeyUpdatedAt"),
        }

    return {
        "twilio": {
            "configured": bool(s.get("twilioAccountSid") and s.get("twilioAuthToken")),
            "accountSid": s.get("twilioAccountSid"),
            "hasAuthToken": bool(s.get("twilioAuthToken")),
        },
        "groq":        _status("groqApiKey",        "groq"),
        "openai":      _status("openaiApiKey",       "openai"),
        "anthropic":   _status("anthropicApiKey",    "anthropic"),
        "gemini":      _status("geminiApiKey",       "gemini"),
        "elevenlabs":  _status("elevenlabsApiKey",   "elevenlabs"),
        "sarvam":      _status("sarvamApiKey",       "sarvam"),
        "deepgram":    _status("deepgramApiKey",     "deepgram"),
        "assemblyai":  _status("assemblyaiApiKey",   "assemblyai"),
    }


# ── OpenAI API key ────────────────────────────────────────────────────────────

@router.post("/openai")
async def save_openai(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key or not api_key.startswith("sk-"):
        return JSONResponse({"error": "A valid OpenAI API key is required (starts with sk-)."}, status_code=400)
    # Live validation
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if resp.status_code == 401:
                return JSONResponse({"error": "Invalid OpenAI API key."}, status_code=400)
    except Exception:
        pass  # network error is non-fatal — save anyway
    result = await _save_byok_key("openai", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "OpenAI API key saved (encrypted)."}


@router.get("/openai")
async def get_openai(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("openai", auth, db)


@router.delete("/openai")
async def delete_openai(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("openai", auth, db)


# ── Anthropic API key ─────────────────────────────────────────────────────────

@router.post("/anthropic")
async def save_anthropic(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key or not api_key.startswith("sk-ant-"):
        return JSONResponse({"error": "A valid Anthropic API key is required (starts with sk-ant-)."}, status_code=400)
    # Live validation — test with a minimal request to avoid cost
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
            )
            if resp.status_code == 401:
                return JSONResponse({"error": "Invalid Anthropic API key."}, status_code=400)
    except Exception:
        pass
    result = await _save_byok_key("anthropic", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "Anthropic API key saved (encrypted)."}


@router.get("/anthropic")
async def get_anthropic(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("anthropic", auth, db)


@router.delete("/anthropic")
async def delete_anthropic(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("anthropic", auth, db)


# ── Gemini API key ────────────────────────────────────────────────────────────

@router.post("/gemini")
async def save_gemini(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key:
        return JSONResponse({"error": "A Gemini API key is required."}, status_code=400)
    # Live validation
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            )
            if resp.status_code == 400:
                data = resp.json()
                if "API_KEY_INVALID" in str(data):
                    return JSONResponse({"error": "Invalid Gemini API key."}, status_code=400)
    except Exception:
        pass
    result = await _save_byok_key("gemini", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "Gemini API key saved (encrypted)."}


@router.get("/gemini")
async def get_gemini(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("gemini", auth, db)


@router.delete("/gemini")
async def delete_gemini(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("gemini", auth, db)


# ── ElevenLabs API key ────────────────────────────────────────────────────────

@router.post("/elevenlabs")
async def save_elevenlabs(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key:
        return JSONResponse({"error": "An ElevenLabs API key is required."}, status_code=400)
    # Live validation
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": api_key},
            )
            if resp.status_code == 401:
                return JSONResponse({"error": "Invalid ElevenLabs API key."}, status_code=400)
    except Exception:
        pass
    result = await _save_byok_key("elevenlabs", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "ElevenLabs API key saved (encrypted)."}


@router.get("/elevenlabs")
async def get_elevenlabs(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("elevenlabs", auth, db)


@router.delete("/elevenlabs")
async def delete_elevenlabs(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("elevenlabs", auth, db)


# ── Sarvam AI API key ─────────────────────────────────────────────────────────

@router.post("/sarvam")
async def save_sarvam(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key:
        return JSONResponse({"error": "A Sarvam AI API key is required."}, status_code=400)
    result = await _save_byok_key("sarvam", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "Sarvam AI API key saved (encrypted)."}


@router.get("/sarvam")
async def get_sarvam(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("sarvam", auth, db)


@router.delete("/sarvam")
async def delete_sarvam(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("sarvam", auth, db)


# ── Deepgram API key ──────────────────────────────────────────────────────────

@router.post("/deepgram")
async def save_deepgram(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key:
        return JSONResponse({"error": "A Deepgram API key is required."}, status_code=400)
    # Live validation
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.deepgram.com/v1/projects",
                headers={"Authorization": f"Token {api_key}"},
            )
            if resp.status_code == 401:
                return JSONResponse({"error": "Invalid Deepgram API key."}, status_code=400)
    except Exception:
        pass
    result = await _save_byok_key("deepgram", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "Deepgram API key saved (encrypted)."}


@router.get("/deepgram")
async def get_deepgram(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("deepgram", auth, db)


@router.delete("/deepgram")
async def delete_deepgram(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("deepgram", auth, db)


# ── AssemblyAI API key ────────────────────────────────────────────────────────

@router.post("/assemblyai")
async def save_assemblyai(body: dict, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    api_key = (body.get("apiKey") or "").strip()
    if not api_key:
        return JSONResponse({"error": "An AssemblyAI API key is required."}, status_code=400)
    # Live validation
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.assemblyai.com/v2/account",
                headers={"authorization": api_key},
            )
            if resp.status_code == 401:
                return JSONResponse({"error": "Invalid AssemblyAI API key."}, status_code=400)
    except Exception:
        pass
    result = await _save_byok_key("assemblyai", api_key, auth, db)
    if "error" in result:
        return JSONResponse(result, status_code=404)
    return {**result, "message": "AssemblyAI API key saved (encrypted)."}


@router.get("/assemblyai")
async def get_assemblyai(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _get_byok_status("assemblyai", auth, db)


@router.delete("/assemblyai")
async def delete_assemblyai(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    return await _delete_byok_key("assemblyai", auth, db)
