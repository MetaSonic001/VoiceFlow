"""
VoiceFlow Python Backend — main.py
Drop-in replacement for Express backend. Same port (8000), same routes, same DB.
Patent Claims: 9 (encryption), 13 (rate-limiting), 7 (scheduler), 8/12/15 (voice).
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.auth import AuthContext, get_auth
from app.models import Tenant, User, AgentTemplate

logger = logging.getLogger("voiceflow")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

start_time = time.time()

DEMO_TENANT_ID = "demo-tenant"
DEMO_USER_ID = "demo-user"
DEMO_EMAIL = "demo@voiceflow.local"


async def seed_demo():
    """Create demo tenant and user if they don't exist."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Tenant).where(Tenant.id == DEMO_TENANT_ID))
            if not result.scalar_one_or_none():
                db.add(Tenant(
                    id=DEMO_TENANT_ID,
                    name="Demo Organization",
                    domain="demo.voiceflow.local",
                    apiKey=f"sk-demo-{int(time.time())}",
                    isActive=True,
                ))
                await db.flush()
                logger.info("[seed] Created demo tenant")

            result = await db.execute(select(User).where(User.id == DEMO_USER_ID))
            if not result.scalar_one_or_none():
                db.add(User(
                    id=DEMO_USER_ID,
                    email=DEMO_EMAIL,
                    name="Demo User",
                    tenantId=DEMO_TENANT_ID,
                ))
                await db.flush()
                logger.info("[seed] Created demo user")

            # Seed agent templates if empty
            tmpl_result = await db.execute(select(AgentTemplate).limit(1))
            if not tmpl_result.scalar_one_or_none():
                templates = [
                    AgentTemplate(
                        id="customer-support", name="Customer Support",
                        description="Handle customer inquiries, resolve issues, and provide product information",
                        baseSystemPrompt="You are a helpful and professional customer support agent. Answer questions accurately, resolve issues empathetically, and escalate when needed.",
                        defaultCapabilities=["faq", "ticketing", "escalation"],
                        suggestedKnowledgeCategories=["product_docs", "faq", "policies"],
                        defaultTools=["search_knowledge", "create_ticket"],
                        icon="headset",
                    ),
                    AgentTemplate(
                        id="cold-calling", name="Cold Calling",
                        description="Outbound sales calls, lead generation, and appointment setting",
                        baseSystemPrompt="You are a persuasive and friendly sales agent. Engage prospects, qualify their needs, and book meetings with the sales team.",
                        defaultCapabilities=["lead_gen", "appointment_booking", "objection_handling"],
                        suggestedKnowledgeCategories=["product_info", "pricing", "competitor_analysis"],
                        defaultTools=["search_knowledge", "book_appointment"],
                        icon="phone-outgoing",
                    ),
                    AgentTemplate(
                        id="lead-qualification", name="Lead Qualification",
                        description="Qualify and score inbound leads based on criteria",
                        baseSystemPrompt="You are a knowledgeable lead qualification specialist. Ask targeted questions to assess fit, budget, and timeline.",
                        defaultCapabilities=["scoring", "routing", "data_collection"],
                        suggestedKnowledgeCategories=["ideal_customer_profile", "qualification_criteria"],
                        defaultTools=["search_knowledge", "update_crm"],
                        icon="filter",
                    ),
                    AgentTemplate(
                        id="technical-support", name="Technical Support",
                        description="Troubleshoot technical issues and guide users through solutions",
                        baseSystemPrompt="You are an expert technical support engineer. Diagnose issues systematically, provide step-by-step solutions, and escalate complex problems.",
                        defaultCapabilities=["troubleshooting", "diagnostics", "escalation"],
                        suggestedKnowledgeCategories=["technical_docs", "known_issues", "release_notes"],
                        defaultTools=["search_knowledge", "create_ticket", "run_diagnostic"],
                        icon="wrench",
                    ),
                    AgentTemplate(
                        id="receptionist", name="Receptionist",
                        description="Greet callers, route calls, and handle basic inquiries",
                        baseSystemPrompt="You are a professional and friendly receptionist. Greet callers warmly, understand their needs, and route them appropriately.",
                        defaultCapabilities=["call_routing", "scheduling", "faq"],
                        suggestedKnowledgeCategories=["company_directory", "office_hours", "faq"],
                        defaultTools=["search_knowledge", "transfer_call", "book_appointment"],
                        icon="phone",
                    ),
                    AgentTemplate(
                        id="survey", name="Survey Agent",
                        description="Conduct customer satisfaction surveys and collect feedback",
                        baseSystemPrompt="You are a friendly survey agent. Ask questions naturally, record responses accurately, and thank participants.",
                        defaultCapabilities=["data_collection", "sentiment_analysis", "reporting"],
                        suggestedKnowledgeCategories=["survey_questions", "product_info"],
                        defaultTools=["search_knowledge", "record_response"],
                        icon="clipboard",
                    ),
                ]
                for t in templates:
                    db.add(t)
                await db.flush()
                logger.info("[seed] Created %d agent templates", len(templates))

            await db.commit()
        except Exception as e:
            logger.warning(f"[seed] Demo seed failed (non-fatal): {e}")
            await db.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VoiceFlow Python backend...")

    # Verify DB connection
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        logger.info("[db] PostgreSQL connection OK")
    except Exception as e:
        logger.error(f"[db] PostgreSQL connection failed: {e}")

    # Auto-create tables if they don't exist
    try:
        from app.database import engine
        from app.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[db] Tables verified/created")
    except Exception as e:
        logger.warning(f"[db] Table creation failed (non-fatal): {e}")

    await seed_demo()
    logger.info(f"Python backend ready on port {settings.PORT}")

    # Start retraining scheduler (Claim 7)
    from app.services.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield
    # Shutdown
    stop_scheduler()
    logger.info("Shutting down...")


app = FastAPI(
    title="VoiceFlow API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Per-tenant rate limiting (Claim 13) ──────────────────────────────────────

def _tenant_key(request: Request) -> str:
    """Rate-limit key: tenant ID from header, falling back to IP."""
    return request.headers.get("x-tenant-id", get_remote_address(request))

limiter = Limiter(key_func=_tenant_key, storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1")
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        {"error": "Rate limit exceeded. Please slow down.", "retry_after": str(exc.detail)},
        status_code=429,
    )

# CORS — same config as Express
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:8090"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "x-tenant-id", "x-user-id", "x-user-email", "X-API-Key"],
)

# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
@app.post("/health")
async def health():
    uptime = int(time.time() - start_time)
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime": uptime,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "backend": "python-fastapi",
    }


# ── Register all routers (same mount paths as Express index.ts) ──────────────

from app.routes import auth, onboarding, agents, documents, templates, runner
from app.routes import analytics, logs, brands, settings as settings_routes
from app.routes import ingestion, users, retraining, admin, tts, rag
from app.routes import widget, voice, voice_ws, platform

# WITHOUT /api prefix (matches Express)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(settings_routes.router, prefix="/settings", tags=["Settings-NoPrefix"])

# WITH /api prefix (matches Express)
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
app.include_router(runner.router, prefix="/api/runner", tags=["Runner"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["Ingestion"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(retraining.router, prefix="/api/retraining", tags=["Retraining"])
app.include_router(brands.router, prefix="/api/brands", tags=["Brands"])
app.include_router(tts.router, prefix="/api/tts", tags=["TTS"])
app.include_router(widget.router, prefix="/api/widget", tags=["Widget"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(voice_ws.router, prefix="/api/voice", tags=["VoiceWS"])
app.include_router(platform.router, prefix="/api", tags=["Platform"])


# ── Twilio proxy (matches Express /twilio/numbers) ──────────────────────────

@app.get("/twilio/numbers")
async def twilio_numbers(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    """Return Twilio numbers. Requires Twilio credentials in tenant settings."""
    result = await db.execute(select(Tenant).where(Tenant.id == auth.tenant_id))
    tenant = result.scalar_one_or_none()
    s = (tenant.settings or {}) if tenant else {}
    sid = s.get("twilioAccountSid")
    token_enc = s.get("twilioAuthToken")
    if not sid or not token_enc:
        return {"numbers": []}
    from app.services.credentials import decrypt_safe
    token = decrypt_safe(token_enc)
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
                auth=(sid, token),
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "numbers": [
                        {"sid": n.get("sid"), "phone_number": n.get("phone_number"), "friendly_name": n.get("friendly_name")}
                        for n in data.get("incoming_phone_numbers", [])
                    ]
                }
    except Exception:
        pass
    return {"numbers": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
