"""
Persistent audit log writes — shared by platform routes and operational hooks.

Uses AuditLog (resource + resourceId + JSON details). Convention:
  resource="conversation_session" — resourceId matches rag_service session_id
  resource="call" — resourceId is call_logs.id after correlation
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.database import AsyncSessionLocal
from app.models import AuditLog

logger = logging.getLogger("voiceflow.audit")


async def write_audit_log(
    tenant_id: str,
    user_id: Optional[str],
    action: str,
    *,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Fire-and-forget audit row."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(
                AuditLog(
                    tenantId=tenant_id,
                    userId=user_id,
                    action=action,
                    resource=resource,
                    resourceId=resource_id,
                    details=details,
                    ipAddress=ip_address,
                )
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to write audit log action=%s", action)


async def record_session_audit_event(
    tenant_id: str,
    session_id: str,
    agent_id: str,
    action: str,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """
    Correlates with CallLog when analysis.conversation_session_id (or legacy session_id) matches.
    action examples: call_audit.workflow_advance, call_audit.workflow_node, call_audit.transcript_turn
    """
    merged: dict[str, Any] = {"agent_id": agent_id, **(details or {})}
    await write_audit_log(
        tenant_id,
        None,
        action,
        resource="conversation_session",
        resource_id=session_id,
        details=merged,
    )
