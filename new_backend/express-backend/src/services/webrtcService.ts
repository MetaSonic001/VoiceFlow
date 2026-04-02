import { Server as HTTPServer } from 'http';
import { Server as SocketServer, Socket } from 'socket.io';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import axios from 'axios';
import FormData from 'form-data';
import RagService from './ragService';
import { ContextInjector } from './contextInjector';
import { buildSystemPrompt } from './promptAssembly';
import { synthesiseForWebRTC } from './ttsService';
import { getTenantGroqKey } from './credentialsService';

/**
 * WebRTC Voice Service — Real Audio Pipeline
 *
 * Enables browser-to-agent voice calls with server-side audio processing.
 * Uses Socket.IO for transport, Groq Whisper for STT, Chatterbox for TTS,
 * and the same RAG pipeline as Twilio calls.
 *
 * Audio flow:
 *   1. Client captures mic audio via MediaRecorder (WebM/Opus)
 *   2. Client sends binary audio via Socket.IO 'audio:data' event
 *   3. Server transcribes audio using Groq Whisper API
 *   4. Server runs full RAG pipeline (context injection → retrieval → LLM)
 *   5. Server synthesises response audio via Chatterbox TTS
 *   6. Server responds with { text, transcript, audioUrl }
 *   7. Client plays audio from URL and displays transcript
 *
 * Fallback:
 *   Clients without mic access can still send text via 'audio:transcript'.
 *   Both paths use the same RAG pipeline and return TTS audio.
 */

interface WebRTCSession {
  agentId: string;
  tenantId: string;
  sessionId: string;
  startedAt: Date;
  voiceId: string;
  conversation: Array<{ role: 'user' | 'assistant'; content: string }>;
}

const sessions = new Map<string, WebRTCSession>();

// ── Groq Whisper STT ──────────────────────────────────────────────────────

/**
 * Transcribe audio using Groq's Whisper API.
 * Accepts WebM/Opus (browser MediaRecorder default), OGG, WAV, MP3, etc.
 */
async function transcribeAudio(audioBuffer: Buffer, mimeType: string = 'audio/webm', groqApiKey?: string): Promise<string> {
  const apiKey = groqApiKey || process.env.GROQ_API_KEY;
  if (!apiKey) throw new Error('GROQ_API_KEY not configured');

  // Map MIME type to file extension for Groq
  const extMap: Record<string, string> = {
    'audio/webm': 'webm',
    'audio/webm;codecs=opus': 'webm',
    'audio/ogg': 'ogg',
    'audio/ogg;codecs=opus': 'ogg',
    'audio/mp4': 'mp4',
    'audio/wav': 'wav',
    'audio/mpeg': 'mp3',
  };
  const ext = extMap[mimeType] || 'webm';

  const form = new FormData();
  form.append('file', audioBuffer, {
    filename: `recording.${ext}`,
    contentType: mimeType.split(';')[0], // strip codec parameter
  });
  form.append('model', 'whisper-large-v3-turbo');

  const response = await axios.post(
    'https://api.groq.com/openai/v1/audio/transcriptions',
    form,
    {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        ...form.getHeaders(),
      },
      timeout: 15000,
    },
  );

  return (response.data?.text || '').trim();
}

// ── Shared RAG + TTS pipeline ─────────────────────────────────────────────

async function processAndRespond(
  sess: WebRTCSession,
  userText: string,
  prisma: PrismaClient,
  redis: Redis,
): Promise<{ responseText: string; audioUrl: string | null }> {
  const injector = new ContextInjector(prisma, redis);
  let systemPrompt: string;
  let policyRules: any[] = [];
  let conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [];
  let model = 'llama-3.3-70b-versatile';

  // Resolve tenant's own Groq API key (falls back to platform key)
  const tenantGroqKey = await getTenantGroqKey(prisma, sess.tenantId);
  const groqApiKey = tenantGroqKey || undefined;

  try {
    const ctx = await injector.assemble(sess.tenantId, sess.agentId, sess.sessionId);
    systemPrompt = buildSystemPrompt(ctx);
    policyRules = ctx.mergedPolicyRules;
    conversationHistory = ctx.conversationHistory;
    const agent = await prisma.agent.findUnique({
      where: { id: sess.agentId },
      select: { llmPreferences: true },
    });
    const prefs = agent?.llmPreferences as any;
    if (prefs?.model) model = prefs.model;
  } catch {
    systemPrompt = 'You are a helpful AI assistant.';
  }

  const contexts = await RagService.queryDocuments(
    sess.tenantId, sess.agentId, userText, 10, 4096, policyRules,
  );
  const responseText = await RagService.generateResponse(
    systemPrompt, contexts, userText, 4096, conversationHistory, model, groqApiKey,
  );

  // Synthesise response audio via Chatterbox TTS
  const audioUrl = await synthesiseForWebRTC(responseText, sess.voiceId, sess.agentId);

  return { responseText, audioUrl };
}

// ── Socket.IO initialisation ──────────────────────────────────────────────

export function initWebRTCSignaling(
  server: HTTPServer,
  prisma: PrismaClient,
  redis: Redis,
): SocketServer {
  const io = new SocketServer(server, {
    cors: {
      origin: process.env.FRONTEND_URL || '*',
      methods: ['GET', 'POST'],
    },
    path: '/ws',
    maxHttpBufferSize: 5 * 1024 * 1024, // 5 MB — allows ~60s of Opus audio
  });

  io.on('connection', (socket: Socket) => {
    const agentId = socket.handshake.query.agentId as string;
    const tenantId = socket.handshake.query.tenantId as string;

    if (!agentId || !tenantId) {
      socket.emit('error', { message: 'agentId and tenantId are required' });
      socket.disconnect();
      return;
    }

    const sessionId = `webrtc_${socket.id}`;

    // Load the agent's configured voice for TTS
    prisma.agent
      .findUnique({
        where: { id: agentId },
        select: { configuration: { select: { voiceId: true } } },
      })
      .then((agent: any) => {
        const voiceId = agent?.configuration?.voiceId || 'preset-aria';
        sessions.set(socket.id, {
          agentId, tenantId, sessionId, startedAt: new Date(), voiceId, conversation: [],
        });
        socket.emit('session:ready', { sessionId });
      })
      .catch(() => {
        sessions.set(socket.id, {
          agentId, tenantId, sessionId, startedAt: new Date(), voiceId: 'preset-aria', conversation: [],
        });
        socket.emit('session:ready', { sessionId });
      });

    // ── Binary audio from client (real voice) ─────────────────────────
    socket.on('audio:data', async (audioData: ArrayBuffer | Buffer, meta?: { mimeType?: string }) => {
      const sess = sessions.get(socket.id);
      if (!sess) return;

      const buffer = Buffer.isBuffer(audioData) ? audioData : Buffer.from(audioData);
      if (buffer.length < 100) return; // ignore tiny/empty frames

      try {
        // 1. STT via Groq Whisper
        socket.emit('status', { state: 'transcribing' });
        const mimeType = meta?.mimeType || 'audio/webm';
        const tenantKey = await getTenantGroqKey(prisma, sess.tenantId);
        const transcript = await transcribeAudio(buffer, mimeType, tenantKey || undefined);

        if (!transcript) {
          socket.emit('agent:response', {
            text: "I didn't catch that. Could you try again?",
            transcript: '',
            audioUrl: null,
            sessionId: sess.sessionId,
          });
          return;
        }

        sess.conversation.push({ role: 'user', content: transcript });

        // 2. RAG pipeline + TTS
        socket.emit('status', { state: 'thinking' });
        const { responseText, audioUrl } = await processAndRespond(sess, transcript, prisma, redis);

        sess.conversation.push({ role: 'assistant', content: responseText });

        // 3. Persist conversation in Redis
        const convKey = `conversation:${sess.tenantId}:${sess.agentId}:${sess.sessionId}`;
        await redis.setex(convKey, 86400, JSON.stringify(sess.conversation.slice(-20))).catch(() => {});

        socket.emit('agent:response', {
          text: responseText,
          transcript,
          audioUrl,
          sessionId: sess.sessionId,
        });
      } catch (err) {
        console.error('[webrtc] Error processing audio:', err);
        socket.emit('agent:response', {
          text: 'I apologize, I encountered an error. Could you please try again?',
          transcript: '',
          audioUrl: null,
          sessionId: sess.sessionId,
        });
      }
    });

    // ── Text fallback (clients without mic / text mode) ───────────────
    socket.on('audio:transcript', async (data: { text: string }) => {
      const sess = sessions.get(socket.id);
      if (!sess || !data.text?.trim()) return;

      const userText = data.text.trim();
      sess.conversation.push({ role: 'user', content: userText });

      try {
        socket.emit('status', { state: 'thinking' });
        const { responseText, audioUrl } = await processAndRespond(sess, userText, prisma, redis);

        sess.conversation.push({ role: 'assistant', content: responseText });

        const convKey = `conversation:${sess.tenantId}:${sess.agentId}:${sess.sessionId}`;
        await redis.setex(convKey, 86400, JSON.stringify(sess.conversation.slice(-20))).catch(() => {});

        socket.emit('agent:response', {
          text: responseText,
          transcript: userText,
          audioUrl,
          sessionId: sess.sessionId,
        });
      } catch (err) {
        console.error('[webrtc] Error processing transcript:', err);
        socket.emit('agent:response', {
          text: 'I apologize, I encountered an error. Could you please repeat that?',
          transcript: userText,
          audioUrl: null,
          sessionId: sess.sessionId,
        });
      }
    });

    // ── Disconnect — persist CallLog ──────────────────────────────────
    socket.on('disconnect', async () => {
      const sess = sessions.get(socket.id);
      if (!sess) return;
      sessions.delete(socket.id);

      if (sess.conversation.length === 0) return;

      try {
        const endedAt = new Date();
        const durationSeconds = Math.round(
          (endedAt.getTime() - sess.startedAt.getTime()) / 1000,
        );

        const transcript = sess.conversation
          .map((t) => `${t.role === 'user' ? 'Caller' : 'Agent'}: ${t.content}`)
          .join('\n');

        await prisma.callLog.create({
          data: {
            tenantId: sess.tenantId,
            agentId: sess.agentId,
            callerPhone: null,
            startedAt: sess.startedAt,
            endedAt,
            durationSeconds,
            transcript,
          },
        });
      } catch (err) {
        console.error('[webrtc] Error persisting call log:', err);
      }
    });
  });

  console.log('[webrtc] Socket.IO voice service initialized on /ws (server-side STT + TTS)');
  return io;
}
