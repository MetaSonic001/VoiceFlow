import { Router, Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import { v4 as uuidv4 } from 'uuid';
import RagService from '../services/ragService';
import { ContextInjector } from '../services/contextInjector';
import { buildSystemPrompt } from '../services/promptAssembly';

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
 * on their websites. Creates a floating call button, connects via
 * Socket.IO, captures real audio via MediaRecorder, sends it to the
 * server for STT (Groq Whisper) + RAG + TTS (Chatterbox), and plays
 * the response audio back to the user.
 *
 * Falls back to a text input if the browser lacks MediaRecorder/mic access.
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
  var mediaRecorder = null;
  var audioChunks = [];
  var micStream = null;
  var isConnected = false;
  var isRecording = false;
  var isProcessing = false;
  var hasMicSupport = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);

  // ── Styles ──────────────────────────────────────────────────────────
  var css = document.createElement("style");
  css.textContent = [
    "#vf-call-btn{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;background:#4F46E5;color:white;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.3);z-index:99999;transition:all 0.2s;border:none;}",
    "#vf-call-btn:hover{transform:scale(1.1);}",
    "#vf-panel{position:fixed;bottom:92px;right:24px;width:340px;background:white;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.2);z-index:99998;display:none;font-family:-apple-system,BlinkMacSystemFont,sans-serif;overflow:hidden;}",
    "#vf-panel *{box-sizing:border-box;}",
    ".vf-header{background:#4F46E5;color:white;padding:16px;}",
    ".vf-header-name{font-weight:600;font-size:16px;}",
    ".vf-status{font-size:12px;opacity:0.8;margin-top:4px;}",
    ".vf-transcript{padding:12px 16px;max-height:300px;overflow-y:auto;font-size:14px;color:#333;min-height:80px;}",
    ".vf-msg{margin-bottom:10px;padding:8px 12px;border-radius:8px;max-width:85%;}",
    ".vf-msg-user{background:#F3F4F6;margin-left:auto;text-align:right;}",
    ".vf-msg-agent{background:#EEF2FF;}",
    ".vf-msg-label{font-size:11px;color:#888;margin-bottom:2px;}",
    ".vf-controls{padding:12px 16px;border-top:1px solid #eee;display:flex;gap:8px;align-items:center;}",
    ".vf-btn{padding:10px 16px;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;transition:all 0.15s;}",
    ".vf-mic{flex:1;background:#4F46E5;color:white;display:flex;align-items:center;justify-content:center;gap:6px;}",
    ".vf-mic:disabled{opacity:0.6;cursor:not-allowed;}",
    ".vf-mic.recording{background:#EF4444;animation:vf-pulse 1.5s infinite;}",
    ".vf-end{background:#EF4444;color:white;display:none;}",
    ".vf-text-row{display:none;gap:8px;padding:0 16px 12px;}",
    ".vf-text-input{flex:1;padding:8px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none;}",
    ".vf-text-input:focus{border-color:#4F46E5;}",
    ".vf-text-send{background:#4F46E5;color:white;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-size:14px;}",
    "@keyframes vf-pulse{0%,100%{opacity:1;}50%{opacity:0.7;}}"
  ].join("\\n");
  document.head.appendChild(css);

  // ── Create widget UI ────────────────────────────────────────────────
  var btn = document.createElement("button");
  btn.id = "vf-call-btn";
  btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>';

  var panel = document.createElement("div");
  panel.id = "vf-panel";
  panel.innerHTML =
    '<div class="vf-header">' +
      '<div class="vf-header-name">AI Voice Assistant</div>' +
      '<div class="vf-status" id="vf-status">Click to start a voice call</div>' +
    '</div>' +
    '<div class="vf-transcript" id="vf-transcript"></div>' +
    '<div class="vf-controls">' +
      '<button class="vf-btn vf-mic" id="vf-mic">Start Call</button>' +
      '<button class="vf-btn vf-end" id="vf-end">End</button>' +
    '</div>' +
    '<div class="vf-text-row" id="vf-text-row">' +
      '<input class="vf-text-input" id="vf-text-input" placeholder="Type a message..." />' +
      '<button class="vf-text-send" id="vf-text-send">Send</button>' +
    '</div>';

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var panelOpen = false;
  btn.onclick = function() {
    panelOpen = !panelOpen;
    panel.style.display = panelOpen ? "block" : "none";
  };

  var micBtn = document.getElementById("vf-mic");
  var endBtn = document.getElementById("vf-end");
  var statusEl = document.getElementById("vf-status");
  var transcriptEl = document.getElementById("vf-transcript");
  var textRow = document.getElementById("vf-text-row");
  var textInput = document.getElementById("vf-text-input");
  var textSendBtn = document.getElementById("vf-text-send");

  // ── Load Socket.IO client from backend ──────────────────────────────
  var s = document.createElement("script");
  s.src = BACKEND + "/socket.io/socket.io.js";
  s.onload = function() { console.log("[VoiceFlow] Widget ready"); };
  document.head.appendChild(s);

  // ── Fetch agent config ──────────────────────────────────────────────
  fetch(BACKEND + "/api/widget/" + AGENT_ID)
    .then(function(r) { return r.json(); })
    .then(function(c) {
      config = c;
      var header = panel.querySelector(".vf-header-name");
      if (header) header.textContent = c.agentName || "AI Voice Assistant";
    })
    .catch(function(e) { console.error("[VoiceFlow] Config error:", e); });

  // ── Helpers ─────────────────────────────────────────────────────────
  function setStatus(text) { statusEl.textContent = text; }

  function addMessage(role, text) {
    var div = document.createElement("div");
    div.className = "vf-msg " + (role === "user" ? "vf-msg-user" : "vf-msg-agent");
    div.innerHTML =
      '<div class="vf-msg-label">' + (role === "user" ? "You" : (config ? config.agentName : "Agent")) + '</div>' +
      '<div>' + text + '</div>';
    transcriptEl.appendChild(div);
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  function getSupportedMimeType() {
    var types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
    for (var i = 0; i < types.length; i++) {
      if (MediaRecorder.isTypeSupported(types[i])) return types[i];
    }
    return "";
  }

  // ── Socket.IO connection ────────────────────────────────────────────
  function connect() {
    if (!config || !window.io) return;
    socket = window.io(BACKEND, {
      path: "/ws",
      query: { agentId: config.agentId, tenantId: config.tenantId },
    });

    socket.on("session:ready", function() {
      isConnected = true;
      if (hasMicSupport) {
        setStatus("Connected — tap mic to talk");
        micBtn.textContent = "\\uD83C\\uDF99 Tap to Talk";
      } else {
        setStatus("Connected — type your message");
        micBtn.style.display = "none";
        textRow.style.display = "flex";
      }
      endBtn.style.display = "block";
    });

    socket.on("status", function(data) {
      if (data.state === "transcribing") setStatus("Transcribing your speech...");
      else if (data.state === "thinking") setStatus("Thinking...");
    });

    socket.on("agent:response", function(data) {
      isProcessing = false;
      micBtn.disabled = false;

      if (data.transcript) addMessage("user", data.transcript);
      addMessage("agent", data.text);

      if (data.audioUrl) {
        setStatus("Agent speaking...");
        var audio = new Audio(data.audioUrl);
        audio.onended = function() { setReady(); };
        audio.onerror = function() { setReady(); };
        audio.play().catch(function() { setReady(); });
      } else {
        setReady();
      }
    });

    socket.on("error", function(data) {
      setStatus("Error: " + (data.message || "unknown"));
    });

    socket.on("disconnect", function() {
      isConnected = false;
      isRecording = false;
      isProcessing = false;
      setStatus("Disconnected");
      micBtn.textContent = "Start Call";
      micBtn.className = "vf-btn vf-mic";
      endBtn.style.display = "none";
      textRow.style.display = "none";
    });
  }

  function setReady() {
    if (!isConnected) return;
    if (hasMicSupport) {
      setStatus("Tap mic to talk");
      micBtn.textContent = "\\uD83C\\uDF99 Tap to Talk";
      micBtn.className = "vf-btn vf-mic";
    } else {
      setStatus("Type your message");
    }
  }

  // ── Audio recording ─────────────────────────────────────────────────
  function startRecording() {
    if (isRecording || isProcessing || !isConnected) return;
    navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 }
    }).then(function(stream) {
      micStream = stream;
      audioChunks = [];
      var mimeType = getSupportedMimeType();
      mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType: mimeType } : {});
      mediaRecorder.ondataavailable = function(e) {
        if (e.data && e.data.size > 0) audioChunks.push(e.data);
      };
      mediaRecorder.onstop = function() {
        var blob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
        sendAudio(blob, mediaRecorder.mimeType);
        if (micStream) {
          micStream.getTracks().forEach(function(t) { t.stop(); });
          micStream = null;
        }
      };
      mediaRecorder.start();
      isRecording = true;
      micBtn.textContent = "\\u23F9 Tap to Send";
      micBtn.className = "vf-btn vf-mic recording";
      setStatus("Recording — tap when done");
    }).catch(function() {
      setStatus("Microphone access denied — use text instead");
      hasMicSupport = false;
      micBtn.style.display = "none";
      textRow.style.display = "flex";
    });
  }

  function stopRecording() {
    if (!isRecording || !mediaRecorder) return;
    mediaRecorder.stop();
    isRecording = false;
    isProcessing = true;
    micBtn.textContent = "Processing...";
    micBtn.className = "vf-btn vf-mic";
    micBtn.disabled = true;
    setStatus("Processing your audio...");
  }

  function sendAudio(blob, mimeType) {
    if (!socket || !isConnected) return;
    blob.arrayBuffer().then(function(buffer) {
      socket.emit("audio:data", buffer, { mimeType: mimeType || "audio/webm" });
    });
  }

  // ── Text fallback ───────────────────────────────────────────────────
  function sendText() {
    var text = textInput.value.trim();
    if (!text || !socket || !isConnected || isProcessing) return;
    addMessage("user", text);
    textInput.value = "";
    isProcessing = true;
    setStatus("Processing...");
    socket.emit("audio:transcript", { text: text });
  }

  // ── Call management ─────────────────────────────────────────────────
  function endCall() {
    isConnected = false;
    isRecording = false;
    isProcessing = false;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      try { mediaRecorder.stop(); } catch(e) {}
    }
    if (micStream) {
      micStream.getTracks().forEach(function(t) { t.stop(); });
      micStream = null;
    }
    if (socket) { socket.disconnect(); socket = null; }
    setStatus("Call ended");
    micBtn.textContent = "Start Call";
    micBtn.className = "vf-btn vf-mic";
    micBtn.disabled = false;
    micBtn.style.display = "block";
    endBtn.style.display = "none";
    textRow.style.display = "none";
  }

  // ── Event handlers ──────────────────────────────────────────────────
  micBtn.onclick = function() {
    if (!isConnected) {
      transcriptEl.innerHTML = "";
      setStatus("Connecting...");
      micBtn.textContent = "Connecting...";
      connect();
    } else if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  endBtn.onclick = endCall;

  textSendBtn.onclick = sendText;
  textInput.onkeydown = function(e) {
    if (e.key === "Enter") sendText();
  };
})();
`;

  res.setHeader('Content-Type', 'application/javascript');
  res.send(script);
});

// ═══════════════════════════════════════════════════════════════════════════
// Per-Agent REST API — Public integration endpoints
//
// These endpoints let any company integrate a VoiceFlow agent into their
// own application WITHOUT using the embeddable widget. They only need the
// agentId (which is public) and can create sessions, send messages, and
// get responses via simple HTTP calls.
//
// Flow:
//   1. POST /api/widget/:agentId/sessions       → creates a session, returns sessionId
//   2. POST /api/widget/:agentId/sessions/:sid/message  → sends text, returns AI response
//   3. GET  /api/widget/:agentId/sessions/:sid   → gets session transcript
//   4. DELETE /api/widget/:agentId/sessions/:sid  → ends session, persists CallLog
// ═══════════════════════════════════════════════════════════════════════════

/**
 * POST /api/widget/:agentId/sessions
 *
 * Create a new conversation session for this agent.
 * Returns a sessionId that the client uses for subsequent messages.
 */
router.post('/:agentId/sessions', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const redis: Redis = req.app.get('redis');

    const agent = await prisma.agent.findUnique({
      where: { id: req.params.agentId },
      select: { id: true, name: true, tenantId: true, status: true },
    });

    if (!agent || agent.status !== 'active') {
      return res.status(404).json({ error: 'Agent not found or inactive' });
    }

    const sessionId = `api_${uuidv4()}`;

    // Store session metadata in Redis (TTL: 1 hour)
    const sessionData = {
      agentId: agent.id,
      tenantId: agent.tenantId,
      sessionId,
      startedAt: new Date().toISOString(),
    };
    await redis.setex(`widget:session:${sessionId}`, 3600, JSON.stringify(sessionData));

    res.status(201).json({
      sessionId,
      agentId: agent.id,
      agentName: agent.name,
      wsEndpoint: `${req.protocol}://${req.get('host')}/ws`,
    });
  } catch (error) {
    console.error('Error creating session:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * POST /api/widget/:agentId/sessions/:sessionId/message
 *
 * Send a text message to the agent and get a response.
 * Uses the full RAG pipeline: ContextInjector → policy scoring → prompt assembly → LLM.
 */
router.post('/:agentId/sessions/:sessionId/message', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const redis: Redis = req.app.get('redis');

    const { text } = req.body;
    if (!text?.trim()) {
      return res.status(400).json({ error: 'text is required' });
    }

    // Validate session
    const sessionRaw = await redis.get(`widget:session:${req.params.sessionId}`);
    if (!sessionRaw) {
      return res.status(404).json({ error: 'Session not found or expired' });
    }
    const session = JSON.parse(sessionRaw);

    if (session.agentId !== req.params.agentId) {
      return res.status(403).json({ error: 'Session does not belong to this agent' });
    }

    const userText = text.trim();

    // Build full context hierarchy
    const injector = new ContextInjector(prisma, redis);
    let systemPrompt: string;
    let policyRules: any[] = [];
    let conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [];
    let model = 'llama-3.3-70b-versatile';

    try {
      const ctx = await injector.assemble(session.tenantId, session.agentId, session.sessionId);
      systemPrompt = buildSystemPrompt(ctx);
      policyRules = ctx.mergedPolicyRules;
      conversationHistory = ctx.conversationHistory;
      const agent = await prisma.agent.findUnique({ where: { id: session.agentId }, select: { llmPreferences: true } });
      const prefs = agent?.llmPreferences as any;
      if (prefs?.model) model = prefs.model;
    } catch {
      systemPrompt = 'You are a helpful AI assistant.';
    }

    // RAG query with policy scoring
    const contexts = await RagService.queryDocuments(
      session.tenantId, session.agentId, userText, 10, 4096, policyRules,
    );
    const response = await RagService.generateResponse(
      systemPrompt, contexts, userText, 4096, conversationHistory, model,
    );

    // Store conversation in Redis for session continuity
    const convKey = `conversation:${session.tenantId}:${session.agentId}:${session.sessionId}`;
    let conversation: Array<{ role: string; content: string }> = [];
    try {
      const existing = await redis.get(convKey);
      if (existing) conversation = JSON.parse(existing);
    } catch {}
    conversation.push({ role: 'user', content: userText });
    conversation.push({ role: 'assistant', content: response });
    if (conversation.length > 20) conversation = conversation.slice(-20);
    await redis.setex(convKey, 86400, JSON.stringify(conversation));

    // Refresh session TTL
    await redis.expire(`widget:session:${req.params.sessionId}`, 3600);

    res.json({ response, sessionId: session.sessionId });
  } catch (error) {
    console.error('Error processing message:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /api/widget/:agentId/sessions/:sessionId
 *
 * Get the current session transcript.
 */
router.get('/:agentId/sessions/:sessionId', async (req: Request, res: Response) => {
  try {
    const redis: Redis = req.app.get('redis');

    const sessionRaw = await redis.get(`widget:session:${req.params.sessionId}`);
    if (!sessionRaw) {
      return res.status(404).json({ error: 'Session not found or expired' });
    }
    const session = JSON.parse(sessionRaw);

    if (session.agentId !== req.params.agentId) {
      return res.status(403).json({ error: 'Session does not belong to this agent' });
    }

    // Load conversation
    const convKey = `conversation:${session.tenantId}:${session.agentId}:${session.sessionId}`;
    let messages: Array<{ role: string; content: string }> = [];
    try {
      const existing = await redis.get(convKey);
      if (existing) messages = JSON.parse(existing);
    } catch {}

    res.json({
      sessionId: session.sessionId,
      agentId: session.agentId,
      startedAt: session.startedAt,
      messages,
    });
  } catch (error) {
    console.error('Error getting session:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * DELETE /api/widget/:agentId/sessions/:sessionId
 *
 * End a session and persist the conversation as a CallLog.
 */
router.delete('/:agentId/sessions/:sessionId', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const redis: Redis = req.app.get('redis');

    const sessionRaw = await redis.get(`widget:session:${req.params.sessionId}`);
    if (!sessionRaw) {
      return res.status(404).json({ error: 'Session not found or expired' });
    }
    const session = JSON.parse(sessionRaw);

    if (session.agentId !== req.params.agentId) {
      return res.status(403).json({ error: 'Session does not belong to this agent' });
    }

    // Load conversation for CallLog
    const convKey = `conversation:${session.tenantId}:${session.agentId}:${session.sessionId}`;
    let messages: Array<{ role: string; content: string }> = [];
    try {
      const existing = await redis.get(convKey);
      if (existing) messages = JSON.parse(existing);
    } catch {}

    // Persist as CallLog
    if (messages.length > 0) {
      const endedAt = new Date();
      const startedAt = new Date(session.startedAt);
      const durationSeconds = Math.round((endedAt.getTime() - startedAt.getTime()) / 1000);
      const transcript = messages
        .map(m => `${m.role === 'user' ? 'Caller' : 'Agent'}: ${m.content}`)
        .join('\n');

      await prisma.callLog.create({
        data: {
          tenantId: session.tenantId,
          agentId: session.agentId,
          callerPhone: null,
          startedAt,
          endedAt,
          durationSeconds,
          transcript,
        },
      });
    }

    // Clean up Redis keys
    await redis.del(`widget:session:${req.params.sessionId}`);
    await redis.del(convKey);

    res.json({ success: true });
  } catch (error) {
    console.error('Error ending session:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
