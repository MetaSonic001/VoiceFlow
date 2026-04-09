"""
VoiceFlow Python Backend — main.py
Drop-in replacement for Express backend. Same port (8000), same routes, same DB.
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Tenant, User

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

    await seed_demo()
    logger.info(f"Python backend ready on port {settings.PORT}")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="VoiceFlow API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — same config as Express
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
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

# WITHOUT /api prefix (matches Express)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
