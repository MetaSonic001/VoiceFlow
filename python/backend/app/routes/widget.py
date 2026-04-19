"""
/api/widget routes — Public per-agent REST API for third-party integration.
No auth required — these are public endpoints for embedded widgets.

Endpoints:
  GET  /api/widget/:agentId              → Widget config (name, greeting, colors)
  GET  /api/widget/:agentId/embed.js     → Embeddable JavaScript widget
  POST /api/widget/:agentId/sessions     → Create conversation session
  POST /api/widget/:agentId/sessions/:sessionId/message → Send message, get AI response
  GET  /api/widget/:agentId/sessions/:sessionId         → Get session transcript
  DELETE /api/widget/:agentId/sessions/:sessionId       → End session
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Agent, AgentConfiguration, CallLog
from app.services.rag_service import (
    process_query,
    get_conversation_history,
    save_conversation_history,
    delete_conversation_history,
)

logger = logging.getLogger("voiceflow.widget")
router = APIRouter()

# ── Rate-limiting helper (uses the limiter from main.py) ─────────────────────

def _get_limiter():
    """Lazy import to avoid circular import at module load time."""
    from main import limiter
    return limiter


@router.get("/{agent_id}")
async def widget_config(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Return widget configuration for an agent (public, no auth)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Load agent configuration for greeting
    cr = await db.execute(
        select(AgentConfiguration).where(AgentConfiguration.agentId == agent_id)
    )
    config = cr.scalar_one_or_none()

    return {
        "agentId": agent.id,
        "name": agent.name,
        "greeting": (config.agentDescription if config and config.agentDescription
                     else f"Hello! I'm {agent.name}. How can I help you?"),
        "voiceId": config.voiceId if config else None,
        "colors": {"primary": "#6366f1", "background": "#ffffff"},
    }


@router.get("/{agent_id}/embed.js")
async def widget_embed_js(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Return embeddable JavaScript widget for any website."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return PlainTextResponse("console.error('VoiceFlow: Agent not found');", status_code=404)

    js = f"""
(function() {{
  var AGENT_ID = '{agent_id}';
  var API_BASE = window.location.protocol + '//' + window.location.host;

  // Create widget button
  var btn = document.createElement('div');
  btn.id = 'vf-widget-btn';
  btn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';
  btn.style.cssText = 'position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#6366f1;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.15);z-index:9999;';
  document.body.appendChild(btn);

  var chatOpen = false;
  var sessionId = null;
  var chatDiv = null;

  btn.onclick = function() {{
    if (chatOpen) {{ chatDiv.style.display = 'none'; chatOpen = false; return; }}
    if (!chatDiv) {{ createChat(); }}
    chatDiv.style.display = 'flex'; chatOpen = true;
    if (!sessionId) {{ startSession(); }}
  }};

  function createChat() {{
    chatDiv = document.createElement('div');
    chatDiv.style.cssText = 'position:fixed;bottom:90px;right:20px;width:360px;height:500px;background:white;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.15);z-index:9999;display:flex;flex-direction:column;overflow:hidden;';
    chatDiv.innerHTML = '<div style="background:#6366f1;color:white;padding:16px;font-weight:600;">{agent.name}</div><div id="vf-messages" style="flex:1;overflow-y:auto;padding:12px;"></div><div style="padding:12px;border-top:1px solid #eee;display:flex;gap:8px;"><input id="vf-input" type="text" placeholder="Type a message..." style="flex:1;border:1px solid #ddd;border-radius:8px;padding:8px 12px;outline:none;"/><button id="vf-send" style="background:#6366f1;color:white;border:none;border-radius:8px;padding:8px 16px;cursor:pointer;">Send</button></div>';
    document.body.appendChild(chatDiv);
    document.getElementById('vf-send').onclick = sendMessage;
    document.getElementById('vf-input').onkeydown = function(e) {{ if(e.key==='Enter') sendMessage(); }};
  }}

  function addMsg(text, isUser) {{
    var el = document.createElement('div');
    el.style.cssText = 'margin:4px 0;padding:8px 12px;border-radius:12px;max-width:80%;font-size:14px;' + (isUser ? 'background:#6366f1;color:white;margin-left:auto;' : 'background:#f3f4f6;');
    el.textContent = text;
    document.getElementById('vf-messages').appendChild(el);
    document.getElementById('vf-messages').scrollTop = 999999;
  }}

  function startSession() {{
    fetch(API_BASE + '/api/widget/' + AGENT_ID + '/sessions', {{method:'POST',headers:{{'Content-Type':'application/json'}}}})
      .then(function(r) {{ return r.json(); }})
      .then(function(d) {{ sessionId = d.sessionId; if(d.greeting) addMsg(d.greeting, false); }});
  }}

  function sendMessage() {{
    var input = document.getElementById('vf-input');
    var msg = input.value.trim();
    if (!msg || !sessionId) return;
    input.value = '';
    addMsg(msg, true);
    fetch(API_BASE + '/api/widget/' + AGENT_ID + '/sessions/' + sessionId + '/message', {{
      method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify({{message: msg}})
    }}).then(function(r) {{ return r.json(); }}).then(function(d) {{ addMsg(d.response || 'No response', false); }});
  }}
}})();
"""
    return PlainTextResponse(js, media_type="application/javascript")


@router.post("/{agent_id}/sessions")
async def create_session(agent_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a new widget conversation session. Rate-limited to 10/minute per IP."""
    # Apply rate limit: 10 session creations per minute per IP
    try:
        limiter = _get_limiter()
        await limiter._check_request_limit(request, "10/minute")
    except Exception:
        pass  # Rate limit check is best-effort; don't break functionality

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    session_id = f"widget-{uuid.uuid4().hex[:12]}"

    # Get greeting
    cr = await db.execute(
        select(AgentConfiguration).where(AgentConfiguration.agentId == agent_id)
    )
    config = cr.scalar_one_or_none()
    greeting = (config.agentDescription if config and config.agentDescription
                else f"Hello! I'm {agent.name}. How can I help you?")

    # Initialize conversation in Redis
    await save_conversation_history(
        agent.tenantId, agent_id, session_id,
        [{"role": "assistant", "content": greeting}],
    )

    return {"sessionId": session_id, "agentId": agent_id, "greeting": greeting}


@router.post("/{agent_id}/sessions/{session_id}/message")
async def send_message(
    agent_id: str, session_id: str, body: dict, request: Request, db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response via full RAG pipeline. Rate-limited to 30/minute per IP."""
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Full RAG pipeline
    rag_result = await process_query(db, agent.tenantId, agent_id, message, session_id)

    return {
        "response": rag_result.get("response", ""),
        "sessionId": session_id,
        "sources": rag_result.get("sources", []),
    }


@router.get("/{agent_id}/sessions/{session_id}")
async def get_session(agent_id: str, session_id: str, db: AsyncSession = Depends(get_db)):
    """Get session transcript."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    history = await get_conversation_history(agent.tenantId, agent_id, session_id)
    return {"sessionId": session_id, "transcript": history}


@router.delete("/{agent_id}/sessions/{session_id}")
async def end_session(agent_id: str, session_id: str, db: AsyncSession = Depends(get_db)):
    """End session: persist as CallLog and clean up."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Get conversation history before deleting
    history = await get_conversation_history(agent.tenantId, agent_id, session_id)

    # Persist as CallLog
    if history:
        try:
            log = CallLog(
                tenantId=agent.tenantId,
                agentId=agent_id,
                startedAt=datetime.now(timezone.utc),
                endedAt=datetime.now(timezone.utc),
                transcript=json.dumps(history),
            )
            db.add(log)
            await db.commit()
        except Exception:
            logger.exception("Failed to persist widget session as CallLog")

    # Clean up Redis
    await delete_conversation_history(agent.tenantId, agent_id, session_id)

    return {"ended": True, "messagesCount": len(history)}
