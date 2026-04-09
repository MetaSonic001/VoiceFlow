"""
Retraining scheduler — Patent Claim 7.
Nightly cron job that processes approved retraining examples:
1. Finds approved RetrainingExample rows
2. Embeds the ideal Q/A pairs into ChromaDB
3. Marks them as retrained
4. Creates notification for the tenant
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models import RetrainingExample, Agent

logger = logging.getLogger("voiceflow.scheduler")

scheduler = AsyncIOScheduler()


async def retrain_approved_examples():
    """Process all approved retraining examples across all tenants."""
    logger.info("[scheduler] Retraining job started")
    processed = 0

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(RetrainingExample).where(
                    RetrainingExample.status == "approved"
                )
            )
            examples = result.scalars().all()

            if not examples:
                logger.info("[scheduler] No approved examples to process")
                return

            # Group by agent
            by_agent: dict[str, list] = {}
            for ex in examples:
                by_agent.setdefault(ex.agentId, []).append(ex)

            for agent_id, agent_examples in by_agent.items():
                # Get agent for tenant info
                agent_result = await db.execute(
                    select(Agent).where(Agent.id == agent_id)
                )
                agent = agent_result.scalar_one_or_none()
                if not agent:
                    continue

                # Embed ideal responses into ChromaDB
                try:
                    import chromadb
                    from app.config import settings
                    chroma = chromadb.HttpClient(
                        host=settings.CHROMA_HOST,
                        port=settings.CHROMA_PORT,
                    )
                    collection_name = f"tenant_{agent.tenantId}_agent_{agent_id}"
                    collection = chroma.get_or_create_collection(collection_name)

                    ids = []
                    documents = []
                    metadatas = []

                    for ex in agent_examples:
                        doc_text = f"Q: {ex.userQuery}\nA: {ex.idealResponse}"
                        ids.append(f"retrain-{ex.id}")
                        documents.append(doc_text)
                        metadatas.append({
                            "source": "retraining",
                            "agentId": agent_id,
                            "tenantId": agent.tenantId,
                            "type": "retraining_example",
                            "originalBadResponse": ex.badResponse[:200],
                        })

                    if ids:
                        collection.upsert(
                            ids=ids,
                            documents=documents,
                            metadatas=metadatas,
                        )

                    # Mark as retrained
                    for ex in agent_examples:
                        ex.status = "retrained"

                    processed += len(agent_examples)

                    # Create notification
                    from app.routes.platform import create_notification
                    await create_notification(
                        tenant_id=agent.tenantId,
                        title="Retraining Complete",
                        message=f"{len(agent_examples)} examples retrained for agent '{agent.name}'.",
                        notif_type="success",
                        link=f"/agents/{agent_id}",
                    )

                except Exception:
                    logger.exception(f"Failed to retrain examples for agent {agent_id}")
                    continue

            await db.commit()
            logger.info(f"[scheduler] Retraining job completed: {processed} examples processed")

        except Exception:
            logger.exception("[scheduler] Retraining job failed")
            await db.rollback()


def start_scheduler():
    """Start the APScheduler with nightly retraining cron job."""
    scheduler.add_job(
        retrain_approved_examples,
        trigger="cron",
        hour=2,
        minute=0,
        id="nightly_retraining",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[scheduler] APScheduler started — retraining runs nightly at 02:00")


def stop_scheduler():
    """Graceful shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] APScheduler stopped")
