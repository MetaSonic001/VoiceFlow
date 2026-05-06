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
async def widget_embed_js(
    agent_id: str,
    color: str = "#6366f1",
    greeting: str = "",
    widget_name: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Return embeddable JavaScript widget for any website.

    Query params:
      color       — hex primary color, e.g. #14b8a6
      greeting    — opening message shown when widget first opens
      widget_name — override displayed agent name
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return PlainTextResponse("console.error('VoiceFlow: Agent not found');", status_code=404)

    # Sanitise injected values (no quotes / script injection)
    import re as _re
    safe_color = color if _re.match(r'^#[0-9a-fA-F]{3,8}$', color) else "#6366f1"
    safe_name = (widget_name or agent.name or "AI Agent").replace("'", "\\'").replace("\\", "")[:80]
    safe_greeting = greeting.replace("'", "\\'").replace("\\", "")[:240]

    js = r"""
(function() {
  /* VoiceFlow Embeddable Chat Widget — auto-injected */
  var AGENT_ID = '""" + agent_id + r"""';
  var AGENT_NAME = '""" + safe_name + r"""';
  var API_BASE = window.location.protocol + '//' + window.location.host;
  var PRIMARY = '""" + safe_color + r"""';
  var GREETING = '""" + safe_greeting + r"""';

  /* ── Simple Markdown renderer (bold, italic, code, links) ── */
  function md(text) {
    if (!text) return '';
    return text
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,'<em>$1</em>')
      .replace(/`(.+?)`/g,'<code style="background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:0.85em">$1</code>')
      .replace(/\[(.+?)\]\((https?:\/\/[^\)]+)\)/g,'<a href="$2" target="_blank" rel="noopener" style="color:' + PRIMARY + ';text-decoration:underline">$1</a>')
      .replace(/\n/g,'<br>');
  }

  /* ── Typing indicator (3-dot pulse) ── */
  function typingHTML() {
    return '<div id="vf-typing" style="display:flex;gap:4px;padding:8px 12px;background:#f3f4f6;border-radius:12px;width:fit-content;margin:4px 0">' +
      '<span style="width:6px;height:6px;background:#9ca3af;border-radius:50%;animation:vf-bounce 1s infinite"></span>' +
      '<span style="width:6px;height:6px;background:#9ca3af;border-radius:50%;animation:vf-bounce 1s 0.15s infinite"></span>' +
      '<span style="width:6px;height:6px;background:#9ca3af;border-radius:50%;animation:vf-bounce 1s 0.3s infinite"></span>' +
      '</div>';
  }

  /* ── Inject keyframe CSS once ── */
  if (!document.getElementById('vf-styles')) {
    var s = document.createElement('style');
    s.id = 'vf-styles';
    s.textContent = '@keyframes vf-bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}';
    document.head.appendChild(s);
  }

  /* ── Floating button ── */
  var btn = document.createElement('div');
  btn.id = 'vf-widget-btn';
  btn.title = 'Chat with ' + AGENT_NAME;
  btn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';
  btn.style.cssText = 'position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:' + PRIMARY + ';display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.15);z-index:9999;transition:transform 0.2s';
  btn.onmouseenter = function(){btn.style.transform='scale(1.1)'};
  btn.onmouseleave = function(){btn.style.transform='scale(1)'};
  document.body.appendChild(btn);

  var chatOpen = false;
  var sessionId = null;
  var chatDiv = null;
  var sending = false;

  btn.onclick = function() {
    if (chatOpen) { chatDiv.style.display = 'none'; chatOpen = false; return; }
    if (!chatDiv) { createChat(); }
    chatDiv.style.display = 'flex'; chatOpen = true;
    if (!sessionId) { startSession(); }
  };

  function createChat() {
    chatDiv = document.createElement('div');
    chatDiv.style.cssText = 'position:fixed;bottom:90px;right:20px;width:380px;height:520px;background:white;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.18);z-index:9999;display:flex;flex-direction:column;overflow:hidden;font-family:system-ui,-apple-system,sans-serif';
    chatDiv.innerHTML =
      '<div style="background:' + PRIMARY + ';color:white;padding:14px 16px;display:flex;align-items:center;justify-content:space-between">' +
        '<div style="display:flex;align-items:center;gap:10px">' +
          '<div style="width:32px;height:32px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center"><svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg></div>' +
          '<span style="font-weight:600;font-size:15px">' + AGENT_NAME + '</span>' +
        '</div>' +
        '<div style="display:flex;gap:8px">' +
          '<button id="vf-call-btn" title="Request a call back" style="background:rgba(255,255,255,0.15);border:none;color:white;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px;display:flex;align-items:center;gap:4px"><svg width="12" height="12" viewBox="0 0 24 24" fill="white"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>Call me</button>' +
          '<button onclick="document.getElementById(\'vf-widget-chat\').style.display=\'none\';chatOpen=false;" style="background:none;border:none;color:rgba(255,255,255,0.8);cursor:pointer;font-size:18px;padding:2px 6px">×</button>' +
        '</div>' +
      '</div>' +
      '<div id="vf-messages" style="flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:4px"></div>' +
      '<div style="padding:10px 12px;border-top:1px solid #eee;display:flex;gap:8px;background:#fafafa">' +
        '<input id="vf-input" type="text" placeholder="Type a message…" style="flex:1;border:1px solid #e5e7eb;border-radius:20px;padding:8px 14px;outline:none;font-size:13px;background:white" autocomplete="off">' +
        '<button id="vf-send" style="background:' + PRIMARY + ';color:white;border:none;border-radius:50%;width:36px;height:36px;cursor:pointer;display:flex;align-items:center;justify-content:center"><svg width="16" height="16" viewBox="0 0 24 24" fill="white"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>' +
      '</div>';
    document.body.appendChild(chatDiv);
    document.getElementById('vf-send').onclick = sendMessage;
    document.getElementById('vf-input').onkeydown = function(e) { if(e.key==='Enter'&&!e.shiftKey) { e.preventDefault(); sendMessage(); } };
    document.getElementById('vf-call-btn').onclick = requestCall;
  }

  function addMsg(html, isUser) {
    var el = document.createElement('div');
    el.style.cssText = 'padding:8px 12px;border-radius:12px;max-width:85%;font-size:13px;line-height:1.5;'
      + (isUser ? 'background:' + PRIMARY + ';color:white;margin-left:auto;border-bottom-right-radius:4px;' : 'background:#f3f4f6;color:#1f2937;border-bottom-left-radius:4px;');
    el.innerHTML = isUser ? html.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : md(html);
    document.getElementById('vf-messages').appendChild(el);
    document.getElementById('vf-messages').scrollTop = 999999;
  }

  function showTyping() {
    var msgs = document.getElementById('vf-messages');
    if (!msgs) return;
    var div = document.createElement('div');
    div.id = 'vf-typing-wrap';
    div.innerHTML = typingHTML();
    msgs.appendChild(div);
    msgs.scrollTop = 999999;
  }
  function hideTyping() {
    var el = document.getElementById('vf-typing-wrap');
    if (el) el.remove();
  }

  function startSession() {
    fetch(API_BASE + '/api/widget/' + AGENT_ID + '/sessions', {method:'POST',headers:{'Content-Type':'application/json'}})
      .then(function(r) { return r.json(); })
      .then(function(d) {
        sessionId = d.sessionId;
        var greet = d.greeting || GREETING;
        if (greet) addMsg(greet, false);
      })
      .catch(function(){});
  }

  function sendMessage() {
    var input = document.getElementById('vf-input');
    if (!input) return;
    var msg = input.value.trim();
    if (!msg || !sessionId || sending) return;
    input.value = '';
    sending = true;
    addMsg(msg, true);
    showTyping();
    fetch(API_BASE + '/api/widget/' + AGENT_ID + '/sessions/' + sessionId + '/message', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: msg})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { hideTyping(); addMsg(d.response || '…', false); sending = false; })
    .catch(function(){ hideTyping(); addMsg('Sorry, something went wrong. Please try again.', false); sending = false; });
  }

  function requestCall() {
    var phone = prompt('Enter your phone number (E.164 format, e.g. +14155551234):');
    if (!phone) return;
    fetch(API_BASE + '/api/widget/' + AGENT_ID + '/call-request', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({phone: phone, sessionId: sessionId})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) { addMsg(d.message || 'Call back requested! We will call you shortly.', false); })
    .catch(function(){ addMsg('Could not request call back. Please try again later.', false); });
  }
})();
"""
    return PlainTextResponse(js, media_type="application/javascript")


@router.post("/{agent_id}/call-request")
async def call_request(agent_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Widget 'Call me' button — record a callback request."""
    phone = (body.get("phone") or "").strip()
    session_id = body.get("sessionId", "")
    if not phone:
        return JSONResponse({"error": "phone is required"}, status_code=400)

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    # Log callback request in Redis (expires after 24h)
    try:
        import redis.asyncio as aioredis
        from app.config import settings as _settings
        r = aioredis.Redis(host=_settings.REDIS_HOST, port=_settings.REDIS_PORT, db=3)
        import json as _json
        await r.setex(
            f"callback:{agent_id}:{uuid.uuid4().hex[:8]}",
            86400,
            _json.dumps({"phone": phone, "agentId": agent_id, "sessionId": session_id}),
        )
        await r.aclose()
    except Exception:
        pass  # non-fatal

    return {"message": "Callback request received. An agent will call you back shortly.", "phone": phone}


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
