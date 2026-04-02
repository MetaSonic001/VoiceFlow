import { Router, Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';

const router = Router();

/**
 * GET /api/widget/:agentId
 *
 * Returns the widget configuration for an agent, used by the embeddable
 * JavaScript snippet. No authentication required — the agentId is the
 * public identifier. Sensitive data is NOT exposed.
 */
router.get('/:agentId', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const agent = await prisma.agent.findUnique({
      where: { id: req.params.agentId },
      select: {
        id: true,
        name: true,
        tenantId: true,
        status: true,
        voiceType: true,
        tenant: { select: { name: true } },
      },
    });

    if (!agent || agent.status !== 'active') {
      return res.status(404).json({ error: 'Agent not found or inactive' });
    }

    res.json({
      agentId: agent.id,
      agentName: agent.name,
      tenantId: agent.tenantId,
      tenantName: agent.tenant.name,
      voiceType: agent.voiceType,
      wsEndpoint: `${req.protocol}://${req.get('host')}/ws`,
    });
  } catch (error) {
    console.error('Error fetching widget config:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /api/widget/:agentId/embed.js
 *
 * Returns a self-contained JavaScript snippet that businesses embed
 * on their websites. It creates a floating call button, connects
 * to the WebRTC signaling layer via Socket.IO, and uses the
 * browser's Web Speech API for speech recognition + synthesis.
 */
router.get('/:agentId/embed.js', async (req: Request, res: Response) => {
  const backendUrl = `${req.protocol}://${req.get('host')}`;
  const agentId = req.params.agentId;

  const script = `
(function() {
  if (window.__voiceflow_widget_loaded) return;
  window.__voiceflow_widget_loaded = true;

  var BACKEND = "${backendUrl}";
  var AGENT_ID = "${agentId}";
  var config = null;
  var socket = null;
  var recognition = null;
  var synthesis = window.speechSynthesis;
  var isListening = false;
  var isConnected = false;

  // ── Create widget UI ────────────────────────────────────────────────
  var btn = document.createElement("div");
  btn.id = "vf-call-btn";
  btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>';
  btn.style.cssText = "position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:#4F46E5;color:white;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.3);z-index:99999;transition:all 0.2s;";
  btn.onmouseenter = function() { btn.style.transform = "scale(1.1)"; };
  btn.onmouseleave = function() { btn.style.transform = "scale(1)"; };

  var panel = document.createElement("div");
  panel.id = "vf-call-panel";
  panel.style.cssText = "position:fixed;bottom:92px;right:24px;width:320px;background:white;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.2);z-index:99998;display:none;font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden;";
  panel.innerHTML = '<div style="background:#4F46E5;color:white;padding:16px;"><div style="font-weight:600;font-size:16px;">AI Voice Assistant</div><div id="vf-status" style="font-size:12px;opacity:0.8;margin-top:4px;">Click to start talking</div></div><div id="vf-transcript" style="padding:16px;max-height:300px;overflow-y:auto;font-size:14px;color:#333;"></div><div style="padding:12px 16px;border-top:1px solid #eee;display:flex;gap:8px;"><button id="vf-mic-btn" style="flex:1;padding:10px;border:none;border-radius:8px;background:#4F46E5;color:white;cursor:pointer;font-size:14px;font-weight:500;">Start Call</button><button id="vf-end-btn" style="padding:10px 16px;border:none;border-radius:8px;background:#EF4444;color:white;cursor:pointer;font-size:14px;font-weight:500;display:none;">End</button></div>';

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var panelOpen = false;
  btn.onclick = function() {
    panelOpen = !panelOpen;
    panel.style.display = panelOpen ? "block" : "none";
  };

  // ── Load Socket.IO from backend ─────────────────────────────────────
  var s = document.createElement("script");
  s.src = BACKEND + "/socket.io/socket.io.js";
  s.onload = function() { console.log("[VoiceFlow] Widget ready"); };
  document.head.appendChild(s);

  // ── Fetch agent config ──────────────────────────────────────────────
  fetch(BACKEND + "/api/widget/" + AGENT_ID)
    .then(function(r) { return r.json(); })
    .then(function(c) {
      config = c;
      var header = panel.querySelector("div > div:first-child");
      if (header) header.textContent = c.agentName || "AI Voice Assistant";
    })
    .catch(function(e) { console.error("[VoiceFlow] Config error:", e); });

  // ── Socket + Speech handlers ────────────────────────────────────────
  var micBtn = document.getElementById("vf-mic-btn");
  var endBtn = document.getElementById("vf-end-btn");
  var statusEl = document.getElementById("vf-status");
  var transcriptEl = document.getElementById("vf-transcript");

  function addMessage(role, text) {
    var div = document.createElement("div");
    div.style.cssText = "margin-bottom:12px;padding:8px 12px;border-radius:8px;" +
      (role === "user"
        ? "background:#F3F4F6;text-align:right;"
        : "background:#EEF2FF;");
    div.innerHTML = "<div style='font-size:11px;color:#888;margin-bottom:2px;'>" +
      (role === "user" ? "You" : config ? config.agentName : "Agent") +
      "</div><div>" + text + "</div>";
    transcriptEl.appendChild(div);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  function connect() {
    if (!config || !window.io) return;
    socket = window.io(BACKEND, {
      path: "/ws",
      query: { agentId: config.agentId, tenantId: config.tenantId },
    });
    socket.on("session:ready", function() {
      isConnected = true;
      statusEl.textContent = "Connected — listening...";
      startListening();
    });
    socket.on("agent:response", function(data) {
      addMessage("agent", data.text);
      speak(data.text);
      // Resume listening after agent finishes speaking
      setTimeout(function() { if (isConnected) startListening(); }, 500);
    });
    socket.on("disconnect", function() {
      isConnected = false;
      statusEl.textContent = "Disconnected";
    });
  }

  function startListening() {
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
      statusEl.textContent = "Speech recognition not supported in this browser";
      return;
    }
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = function(event) {
      var text = event.results[0][0].transcript;
      addMessage("user", text);
      statusEl.textContent = "Processing...";
      if (socket && isConnected) {
        socket.emit("audio:transcript", { text: text });
      }
    };
    recognition.onerror = function() {
      if (isConnected) setTimeout(startListening, 1000);
    };
    recognition.onend = function() {
      // Don't auto-restart here — we restart after agent responds
    };
    isListening = true;
    statusEl.textContent = "Listening...";
    recognition.start();
  }

  function speak(text) {
    if (!synthesis) return;
    synthesis.cancel();
    var utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1;
    utter.pitch = 1;
    synthesis.speak(utter);
  }

  function endCall() {
    isConnected = false;
    isListening = false;
    if (recognition) { try { recognition.stop(); } catch(e){} }
    if (socket) { socket.disconnect(); socket = null; }
    statusEl.textContent = "Call ended";
    micBtn.textContent = "Start Call";
    micBtn.style.background = "#4F46E5";
    endBtn.style.display = "none";
  }

  micBtn.onclick = function() {
    if (isConnected) return;
    transcriptEl.innerHTML = "";
    statusEl.textContent = "Connecting...";
    micBtn.textContent = "Listening...";
    micBtn.style.background = "#22C55E";
    endBtn.style.display = "block";
    connect();
  };
  endBtn.onclick = endCall;
})();
`;

  res.setHeader('Content-Type', 'application/javascript');
  res.send(script);
});

export default router;
