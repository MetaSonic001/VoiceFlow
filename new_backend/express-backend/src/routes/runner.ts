import express, { Request, Response, NextFunction, Router } from 'express';
import Joi from 'joi';
import { PrismaClient } from '@prisma/client';
import multer from 'multer';
import RagService from '../services/ragService';
import VoiceService from '../services/voiceService';
import { TwilioMediaService, TwilioMediaConfig } from '../services/twilioMediaService';
import { getTenantTwilioCreds } from '../services/twilioClientService';
import dotenv from 'dotenv';
dotenv.config();

const router: Router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

// Import services (they are singleton instances)
const ragService = RagService;
const voiceService = VoiceService;

// Lazy-init TwilioMediaService per-tenant to avoid hardcoded env credentials
const mediaServiceCache = new Map<string, TwilioMediaService>();

async function getMediaService(req: Request): Promise<TwilioMediaService> {
  const tenantId = req.tenantId || 'default';
  const cached = mediaServiceCache.get(tenantId);
  if (cached) return cached;

  const prisma: PrismaClient = req.app.get('prisma');
  let accountSid = '';
  let authToken = '';

  // Prefer per-tenant creds, fall back to env vars
  const creds = await getTenantTwilioCreds(prisma, tenantId).catch(() => null);
  if (creds) {
    accountSid = creds.accountSid;
    authToken = creds.authToken;
  } else {
    accountSid = process.env.TWILIO_ACCOUNT_SID || '';
    authToken = process.env.TWILIO_AUTH_TOKEN || '';
  }

  const config: TwilioMediaConfig = {
    accountSid,
    authToken,
    phoneNumber: process.env.TWILIO_PHONE_NUMBER || '',
    voskModelPath: process.env.VOSK_MODEL_PATH || './models/vosk-model',
  };
  const svc = new TwilioMediaService(config, ragService, voiceService);
  mediaServiceCache.set(tenantId, svc);
  // Expire cache entry after 5 minutes
  setTimeout(() => mediaServiceCache.delete(tenantId), 5 * 60 * 1000);
  return svc;
}

// Interfaces
interface ChatBody {
  message: string;
  agentId: string;
  sessionId?: string;
}

// Validation schemas
const chatSchema = Joi.object({
  message: Joi.string().required().min(1).max(1000),
  agentId: Joi.string().required(),
  sessionId: Joi.string().optional()
});

// Chat with agent (for frontend)
router.post('/chat', async (req: Request, res: Response) => {
  try {
    const { error, value } = chatSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { message, agentId, sessionId } = value as ChatBody;

    // Verify agent belongs to tenant or use default for testing
    let agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        tenantId: req.tenantId
      }
    });

    // If agent not found, use default configuration for testing
    if (!agent) {
      if (agentId === 'test-agent' || agentId === 'voice-agent') {
        agent = {
          id: agentId,
          name: 'Test Agent',
          systemPrompt: 'You are a helpful AI assistant. Provide clear, accurate, and concise responses.',
          tokenLimit: 2000
        } as any;
      } else {
        return res.status(403).json({ error: 'Access denied' });
      }
    }

    const response = await ragService.processQuery(
      req.tenantId,
      agentId,
      message,
      {
        systemPrompt: agent!.systemPrompt || undefined,
        tokenLimit: agent!.tokenLimit || undefined
      },
      sessionId
    );

    res.json({
      response: response,
      agentId: agentId,
      sessionId: sessionId || 'default'
    });
  } catch (error) {
    console.error('Error in chat:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get agent info for frontend
router.get('/agent/:agentId', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { agentId } = req.params;

    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        tenantId: req.tenantId
      },
      select: {
        id: true,
        name: true,
        systemPrompt: true,
        voiceType: true,
        llmPreferences: true,
        tokenLimit: true,
        contextWindowStrategy: true,
        createdAt: true,
        _count: {
          select: { documents: true }
        }
      }
    });

    if (!agent) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    res.json(agent);
  } catch (error) {
    console.error('Error fetching agent info:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Audio processing for voice interface
router.post('/audio', upload.single('audio'), async (req: Request, res: Response) => {
  try {
    const { agentId, sessionId } = req.body;

    if (!req.file) {
      return res.status(400).json({ error: 'No audio file provided' });
    }

    const audioBuffer = req.file.buffer;

    // Process audio (this will do ASR and generate response)
    const mediaService = await getMediaService(req);
    const result = await mediaService.processAudioForWeb(audioBuffer, agentId, sessionId || 'default');

    res.json({
      transcript: result.transcript,
      response: result.response,
      agentId: agentId,
      sessionId: sessionId || 'default'
    });
  } catch (error) {
    console.error('Error processing audio:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;