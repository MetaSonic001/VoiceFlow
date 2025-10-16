import express, { Request, Response, NextFunction } from 'express';
import Joi from 'joi';
import { PrismaClient } from '@prisma/client';

const router = express.Router();

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
    }
  }
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

// Middleware to validate tenant access
const validateTenantAccess = (req: Request, res: Response, next: NextFunction) => {
  const tenantId = req.headers['x-tenant-id'] || req.query.tenantId;
  if (!tenantId || typeof tenantId !== 'string') {
    return res.status(400).json({ error: 'Tenant ID required' });
  }
  req.tenantId = tenantId;
  next();
};

// Chat with agent (for frontend)
router.post('/chat', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const { error, value } = chatSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { message, agentId, sessionId } = value as ChatBody;

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

    const ragService = require('../services/ragService');
    const response = await ragService.processQuery(
      req.tenantId,
      agentId,
      message,
      agent,
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
router.get('/agent/:agentId', validateTenantAccess, async (req: Request, res: Response) => {
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

// List user's agents for frontend
router.get('/agents', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { userId } = req.query;

    if (!userId || typeof userId !== 'string') {
      return res.status(400).json({ error: 'User ID required' });
    }

    const agents = await prisma.agent.findMany({
      where: {
        userId: userId,
        tenantId: req.tenantId
      },
      select: {
        id: true,
        name: true,
        voiceType: true,
        createdAt: true,
        _count: {
          select: { documents: true }
        }
      },
      orderBy: { createdAt: 'desc' }
    });

    res.json(agents);
  } catch (error) {
    console.error('Error fetching agents:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;