import express, { Request, Response, NextFunction, Router } from 'express';
import Joi from 'joi';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import RagService from '../services/ragService';
import { assembleSystemPrompt, buildSystemPrompt } from '../services/promptAssembly';
import { ContextInjector } from '../services/contextInjector';

const router: Router = express.Router();

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
    }
  }
}

// Interfaces
interface QueryBody {
  query: string;
  agentId: string;
  sessionId?: string;
}

// Validation schemas
const querySchema = Joi.object({
  query: Joi.string().required().min(1).max(1000),
  agentId: Joi.string().required(),
  sessionId: Joi.string().optional()
});

// Middleware to validate tenant access
const validateTenantAccess = async (req: Request, res: Response, next: NextFunction) => {
  const tenantId = req.headers['x-tenant-id'] || req.query.tenantId;
  if (!tenantId || typeof tenantId !== 'string') {
    return res.status(400).json({ error: 'Tenant ID required' });
  }

  // Verify tenant exists and is active
  const prisma = req.app.get('prisma') as PrismaClient;
  const tenant = await prisma.tenant.findUnique({
    where: { id: tenantId, isActive: true }
  });

  if (!tenant) {
    return res.status(403).json({ error: 'Invalid or inactive tenant' });
  }

  req.tenantId = tenantId;
  next();
};

// Query agent with RAG — full 5-layer context hierarchy
router.post('/query', async (req: Request, res: Response) => {
  try {
    const { error, value } = querySchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const redis: Redis = req.app.get('redis');
    const { query, agentId, sessionId = 'default' } = value as QueryBody;

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        tenantId: req.tenantId
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    // ── Assemble full context hierarchy ────────────────────────────────
    const injector = new ContextInjector(prisma, redis);
    let systemPrompt: string;
    let policyRules: any[] = [];

    try {
      const ctx = await injector.assemble(req.tenantId, agentId, sessionId);
      systemPrompt = buildSystemPrompt(ctx);
      policyRules = ctx.mergedPolicyRules;
    } catch {
      // Fallback to legacy assembler
      systemPrompt = await assembleSystemPrompt(prisma, agentId, req.tenantId);
    }

    const startedAt = new Date();
    const contexts = await RagService.queryDocuments(
      req.tenantId, agentId, query, 10, agent.tokenLimit || 4096, policyRules,
    );
    const response = await RagService.generateResponse(
      systemPrompt, contexts, query, agent.tokenLimit || 4096,
    );

    // Store conversation turn in Redis
    const convKey = `conversation:${req.tenantId}:${agentId}:${sessionId}`;
    try {
      const rawConv = await redis.get(convKey);
      let conversation = rawConv ? JSON.parse(rawConv) : [];
      conversation.push({ role: 'user', content: query });
      conversation.push({ role: 'assistant', content: response });
      if (conversation.length > 20) conversation = conversation.slice(-20);
      await redis.setex(convKey, 86400, JSON.stringify(conversation));
    } catch (redisErr) {
      console.warn('Redis error storing conversation:', redisErr);
    }

    const endedAt = new Date();

    // Fire-and-forget CallLog write
    prisma.callLog.create({
      data: {
        tenantId: req.tenantId,
        agentId,
        startedAt,
        endedAt,
        durationSeconds: Math.round((endedAt.getTime() - startedAt.getTime()) / 1000),
        transcript: `Q: ${query}\nA: ${typeof response === 'string' ? response : JSON.stringify(response)}`,
      },
    }).catch((err: Error) => console.error('CallLog write failed:', err));

    res.json({
      response: response,
      agentId: agentId,
      sessionId: sessionId
    });
  } catch (error) {
    console.error('Error processing RAG query:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get conversation history
router.get('/conversation/:sessionId', async (req: Request, res: Response) => {
  try {
    const { sessionId } = req.params;
    const { agentId } = req.query;

    if (!agentId || typeof agentId !== 'string') {
      return res.status(400).json({ error: 'Agent ID required' });
    }

    const prisma: PrismaClient = req.app.get('prisma');

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        tenantId: req.tenantId
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const redis = req.app.get('redis');
    const conversationKey = `conversation:${req.tenantId}:${agentId}:${sessionId}`;
    const conversation = await redis.get(conversationKey);

    res.json({
      sessionId: sessionId,
      conversation: conversation ? JSON.parse(conversation) : []
    });
  } catch (error) {
    console.error('Error fetching conversation:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Clear conversation history
router.delete('/conversation/:sessionId', async (req: Request, res: Response) => {
  try {
    const { sessionId } = req.params;
    const { agentId } = req.query;

    if (!agentId || typeof agentId !== 'string') {
      return res.status(400).json({ error: 'Agent ID required' });
    }

    const prisma: PrismaClient = req.app.get('prisma');

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        tenantId: req.tenantId
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const redis = req.app.get('redis');
    const conversationKey = `conversation:${req.tenantId}:${agentId}:${sessionId}`;
    await redis.del(conversationKey);

    res.status(204).send();
  } catch (error) {
    console.error('Error clearing conversation:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;