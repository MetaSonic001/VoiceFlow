import { Router, Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import twilio from 'twilio';
import { assembleSystemPrompt } from '../services/promptAssembly';
import RagService from '../services/ragService';
import { analyzeCall } from '../services/callAnalysis';
import { getTwilioAuthTokenForValidation } from '../services/twilioClientService';
import { synthesiseForCall } from '../services/ttsService';
import { getTenantGroqKey } from '../services/credentialsService';

const router = Router();
const { VoiceResponse } = twilio.twiml;

// ─── Config ──────────────────────────────────────────────────────────────────

const WEBHOOK_BASE = process.env.TWILIO_WEBHOOK_BASE_URL || '';

const EXIT_KEYWORDS = [
  'bye', 'goodbye', 'good bye', 'thank you', 'thanks',
  "that's all", 'end call', 'hang up', 'no more questions',
  'nothing else', 'i am done', "i'm done",
];

// ─── Types ───────────────────────────────────────────────────────────────────

interface TwilioSession {
  agentId: string;
  tenantId: string;
  startedAt: string;
  callerPhone: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getPrisma(req: Request): PrismaClient {
  return req.app.get('prisma') as PrismaClient;
}

function getRedis(req: Request): Redis {
  return req.app.get('redis') as Redis;
}

/**
 * Validate the x-twilio-signature header against the tenant's auth token.
 * Skipped in development when TWILIO_WEBHOOK_BASE_URL is not set.
 */
function validateSignature(req: Request, authToken: string): boolean {
  if (!WEBHOOK_BASE) return true;
  const signature = req.headers['x-twilio-signature'] as string;
  if (!signature) return false;
  const url = `${WEBHOOK_BASE}${req.originalUrl}`;
  return twilio.validateRequest(authToken, signature, url, req.body);
}

function isExitIntent(text: string): boolean {
  const lower = text.toLowerCase().trim();
  return EXIT_KEYWORDS.some((kw) => lower.includes(kw));
}

/**
 * Speak text via <Say> or <Play> if a TTS audio URL is available (Task 13).
 */
function speak(response: InstanceType<typeof VoiceResponse>, text: string, audioUrl?: string): void {
  if (audioUrl) {
    response.play(audioUrl);
  } else {
    response.say({ voice: 'Polly.Aditi', language: 'en-IN' }, text);
  }
}

/**
 * Append a <Gather> element configured for conversational speech recognition.
 */
function appendGather(response: InstanceType<typeof VoiceResponse>): void {
  response.gather({
    input: ['speech'],
    action: '/twilio/voice/respond',
    method: 'POST',
    speechTimeout: 'auto',
    speechModel: 'experimental_conversations',
    actionOnEmptyResult: true,
    language: 'en-IN',
  });
}

// ─── POST /incoming ──────────────────────────────────────────────────────────
// Twilio calls this when someone dials the agent's provisioned number.

router.post('/incoming', async (req: Request, res: Response) => {
  const prisma = getPrisma(req);
  const redis = getRedis(req);
  const response = new VoiceResponse();

  try {
    const toNumber = (req.body.To as string) || '';
    const callSid = req.body.CallSid as string;
    const callerPhone = (req.body.From as string) || 'unknown';

    // Look up agent by provisioned phone number
    const agent = await prisma.agent.findFirst({
      where: { phoneNumber: toNumber, status: 'active' },
      include: { tenant: true, configuration: true },
    });

    if (!agent) {
      response.say(
        { voice: 'Polly.Aditi', language: 'en-IN' },
        'Sorry, this number is no longer active. Please contact the company directly.',
      );
      response.hangup();
      res.type('text/xml').send(response.toString());
      return;
    }

    // Validate Twilio request signature
    const authToken = await getTwilioAuthTokenForValidation(prisma, agent.tenantId);
    if (authToken && WEBHOOK_BASE && !validateSignature(req, authToken)) {
      res.status(403).send('Invalid Twilio signature');
      return;
    }

    // Store session in Redis (TTL 2 hours)
    const session: TwilioSession = {
      agentId: agent.id,
      tenantId: agent.tenantId,
      startedAt: new Date().toISOString(),
      callerPhone,
    };
    await redis.setex(`twilio:session:${callSid}`, 7200, JSON.stringify(session));

    // Build greeting from agent & company names
    const config = agent.configuration;
    const tenantSettings = (agent.tenant?.settings as Record<string, any>) || {};
    const agentName = config?.agentName || agent.name || 'your assistant';
    const companyName =
      config?.companyName || tenantSettings.companyName || agent.tenant?.name || '';

    const greeting = companyName
      ? `Hello! You've reached ${companyName}. I'm ${agentName}. How can I help you today?`
      : `Hello! I'm ${agentName}. How can I help you today?`;

    // Synthesise greeting with the agent's configured voice (falls back to <Say>)
    const voiceId = config?.voiceId || 'preset-aria';
    const greetingAudioUrl = await synthesiseForCall(greeting, voiceId, agent.id);

    // TwiML: greeting → gather speech → redirect fallback
    speak(response, greeting, greetingAudioUrl ?? undefined);
    appendGather(response);
    response.redirect({ method: 'POST' }, '/twilio/voice/incoming');

    res.type('text/xml').send(response.toString());
  } catch (error) {
    console.error('[twilio/incoming] Error:', error);
    speak(response, 'We are experiencing technical difficulties. Please try again later.');
    response.hangup();
    res.type('text/xml').send(response.toString());
  }
});

// ─── POST /respond ───────────────────────────────────────────────────────────
// Twilio calls this after <Gather> transcribes the caller's speech.

router.post('/respond', async (req: Request, res: Response) => {
  const prisma = getPrisma(req);
  const redis = getRedis(req);
  const response = new VoiceResponse();

  try {
    const callSid = req.body.CallSid as string;
    const speechResult = ((req.body.SpeechResult as string) || '').trim();

    // Load session
    const sessionData = await redis.get(`twilio:session:${callSid}`);
    if (!sessionData) {
      speak(response, 'Sorry, your session has expired. Please call back.');
      response.hangup();
      res.type('text/xml').send(response.toString());
      return;
    }
    const session: TwilioSession = JSON.parse(sessionData);

    // Validate signature (requires DB lookup for tenant auth token)
    const agent = await prisma.agent.findFirst({
      where: { id: session.agentId },
      include: { tenant: true, configuration: true },
    });
    if (agent) {
      const authToken = await getTwilioAuthTokenForValidation(prisma, agent.tenantId);
      if (authToken && WEBHOOK_BASE && !validateSignature(req, authToken)) {
        res.status(403).send('Invalid Twilio signature');
        return;
      }
    }

    // ── Empty speech ─────────────────────────────────────────────────────
    if (!speechResult) {
      speak(response, "I didn't catch that. Could you please repeat?");
      appendGather(response);
      response.redirect({ method: 'POST' }, '/twilio/voice/incoming');
      res.type('text/xml').send(response.toString());
      return;
    }

    // ── Exit intent ──────────────────────────────────────────────────────
    if (isExitIntent(speechResult)) {
      // Persist the farewell turn so the status callback has the full transcript
      const conversationKey = `conversation:${session.tenantId}:${session.agentId}:${callSid}`;
      try {
        const raw = await redis.get(conversationKey);
        const history = raw ? JSON.parse(raw) : [];
        history.push({ role: 'user', content: speechResult });
        history.push({ role: 'assistant', content: 'Goodbye! Thank you for calling.' });
        await redis.setex(conversationKey, 86400, JSON.stringify(history));
      } catch { /* best-effort */ }

      speak(
        response,
        'Thank you for calling! If you need anything else, feel free to call back anytime. Goodbye!',
      );
      response.hangup();
      res.type('text/xml').send(response.toString());
      return;
    }

    // ── RAG pipeline ─────────────────────────────────────────────────────
    const systemPrompt = await assembleSystemPrompt(prisma, session.agentId, session.tenantId);
    const ragAgent = { systemPrompt, tokenLimit: agent?.tokenLimit || 4096 };
    const tenantGroqKey = await getTenantGroqKey(prisma, session.tenantId);

    const aiResponse = await RagService.processQuery(
      session.tenantId,
      session.agentId,
      speechResult,
      ragAgent,
      callSid, // Use CallSid as the RAG session ID
      tenantGroqKey || undefined,
    );

    // Synthesise AI response with the agent's configured voice
    const voiceId = agent?.configuration?.voiceId || 'preset-aria';
    const audioUrl = await synthesiseForCall(aiResponse, voiceId, session.agentId);
    speak(response, aiResponse, audioUrl ?? undefined);
    appendGather(response);
    response.redirect({ method: 'POST' }, '/twilio/voice/incoming');

    res.type('text/xml').send(response.toString());
  } catch (error) {
    console.error('[twilio/respond] Error:', error);
    speak(response, "I'm sorry, I had trouble processing that. Could you try again?");
    appendGather(response);
    response.redirect({ method: 'POST' }, '/twilio/voice/incoming');
    res.type('text/xml').send(response.toString());
  }
});

// ─── POST /status ────────────────────────────────────────────────────────────
// Twilio calls this when the call ends (CallStatus = "completed").

router.post('/status', async (req: Request, res: Response) => {
  const prisma = getPrisma(req);
  const redis = getRedis(req);

  try {
    const callSid = req.body.CallSid as string;
    const callStatus = req.body.CallStatus as string;
    const callDuration = parseInt(req.body.CallDuration || '0', 10);

    // Only process completed calls
    if (callStatus !== 'completed') {
      res.sendStatus(204);
      return;
    }

    // Load session
    const sessionData = await redis.get(`twilio:session:${callSid}`);
    if (!sessionData) {
      console.warn(`[twilio/status] No session for completed call ${callSid}`);
      res.sendStatus(204);
      return;
    }
    const session: TwilioSession = JSON.parse(sessionData);

    // Validate signature
    const agent = await prisma.agent.findFirst({
      where: { id: session.agentId },
      include: { tenant: true },
    });
    if (agent) {
      const authToken = await getTwilioAuthTokenForValidation(prisma, agent.tenantId);
      if (authToken && WEBHOOK_BASE && !validateSignature(req, authToken)) {
        res.status(403).send('Invalid Twilio signature');
        return;
      }
    }

    // Load conversation history from Redis (same key the RAG service uses)
    const conversationKey = `conversation:${session.tenantId}:${session.agentId}:${callSid}`;
    let conversation: { role: string; content: string }[] = [];
    try {
      const raw = await redis.get(conversationKey);
      if (raw) conversation = JSON.parse(raw);
    } catch { /* */ }

    // Format transcript as readable text
    const transcript = conversation.length
      ? conversation
          .map((m) => `${m.role === 'user' ? 'Caller' : 'Agent'}: ${m.content}`)
          .join('\n')
      : '(no transcript)';

    // Write CallLog to database
    const startedAt = new Date(session.startedAt);
    const callLog = await prisma.callLog.create({
      data: {
        tenantId: session.tenantId,
        agentId: session.agentId,
        callerPhone: session.callerPhone,
        startedAt,
        endedAt: new Date(),
        durationSeconds: callDuration,
        transcript,
      },
    });

    // Non-blocking: run post-call LLM analysis and store result
    analyzeCall(conversation)
      .then(async (analysis) => {
        try {
          await prisma.callLog.update({
            where: { id: callLog.id },
            data: { analysis: analysis as any },
          });
          console.log(`[twilio/status] Analysis saved for call ${callSid}`);
        } catch (e) {
          console.error('[twilio/status] Failed to store analysis:', e);
        }
      })
      .catch((err) => console.error('[twilio/status] Analysis failed:', err));

    // Clean up Redis session and conversation keys
    await redis.del(`twilio:session:${callSid}`);
    await redis.del(conversationKey);

    res.sendStatus(204);
  } catch (error) {
    console.error('[twilio/status] Error:', error);
    res.sendStatus(204); // Always respond to Twilio, even on error
  }
});

// ─── GET /test ───────────────────────────────────────────────────────────────
// Used by the setup flow to confirm the webhook path is reachable.

router.get('/test', (_req: Request, res: Response) => {
  const response = new VoiceResponse();
  response.say('Webhook verified.');
  res.type('text/xml').send(response.toString());
});

export default router;
