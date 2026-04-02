import { Server as HTTPServer } from 'http';
import { Server as SocketServer, Socket } from 'socket.io';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import RagService from './ragService';
import { ContextInjector } from './contextInjector';
import { buildSystemPrompt } from './promptAssembly';

/**
 * WebRTC Signaling Service — Task 26
 *
 * Enables browser-to-agent voice calls over WebRTC without Twilio.
 * Uses Socket.IO for signaling and the same RAG pipeline as Twilio calls.
 *
 * Flow:
 *   1. Client connects via Socket.IO with { agentId, tenantId }
 *   2. Server creates a session and emits 'session:ready'
 *   3. Client sends audio transcription text via 'audio:transcript'
 *   4. Server runs RAG pipeline and responds with 'agent:response'
 *   5. Client uses Web Speech API (browser TTS) or fetches /api/tts for audio
 *   6. On disconnect, server persists CallLog
 */

interface WebRTCSession {
  agentId: string;
  tenantId: string;
  sessionId: string;
  startedAt: Date;
  conversation: Array<{ role: 'user' | 'assistant'; content: string }>;
}

const sessions = new Map<string, WebRTCSession>();

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
    const session: WebRTCSession = {
      agentId,
      tenantId,
      sessionId,
      startedAt: new Date(),
      conversation: [],
    };
    sessions.set(socket.id, session);

    socket.emit('session:ready', { sessionId });

    // ── Client sends transcribed speech text ────────────────────────────
    socket.on('audio:transcript', async (data: { text: string }) => {
      const sess = sessions.get(socket.id);
      if (!sess || !data.text?.trim()) return;

      const userText = data.text.trim();
      sess.conversation.push({ role: 'user', content: userText });

      try {
        // Build full context hierarchy
        const injector = new ContextInjector(prisma, redis);
        let systemPrompt: string;
        let policyRules: any[] = [];

        try {
          const ctx = await injector.assemble(sess.tenantId, sess.agentId, sess.sessionId);
          systemPrompt = buildSystemPrompt(ctx);
          policyRules = ctx.mergedPolicyRules;
        } catch {
          systemPrompt = 'You are a helpful AI assistant.';
        }

        // RAG query with policy scoring
        const contexts = await RagService.queryDocuments(
          sess.tenantId, sess.agentId, userText, 10, 4096, policyRules,
        );
        const response = await RagService.generateResponse(
          systemPrompt, contexts, userText, 4096,
        );

        sess.conversation.push({ role: 'assistant', content: response });

        // Store in Redis for session continuity
        const convKey = `conversation:${sess.tenantId}:${sess.agentId}:${sess.sessionId}`;
        const convSlice = sess.conversation.slice(-20);
        await redis.setex(convKey, 86400, JSON.stringify(convSlice)).catch(() => {});

        socket.emit('agent:response', { text: response, sessionId: sess.sessionId });
      } catch (err) {
        console.error('[webrtc] Error processing transcript:', err);
        socket.emit('agent:response', {
          text: 'I apologize, I encountered an error. Could you please repeat that?',
          sessionId: sess.sessionId,
        });
      }
    });

    // ── Client disconnects — persist CallLog ────────────────────────────
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
            callerPhone: null, // WebRTC — no phone
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

  console.log('[webrtc] Socket.IO signaling initialized on /ws');
  return io;
}
