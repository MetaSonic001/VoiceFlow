import express, { Request, Response, NextFunction, Router } from 'express';
import Joi from 'joi';
import { PrismaClient } from '@prisma/client';

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

interface CreateAgentBody {
  name: string;
  systemPrompt?: string;
  voiceType?: 'male' | 'female';
  llmPreferences?: any;
  tokenLimit?: number;
  contextWindowStrategy?: 'condense' | 'truncate';
}

interface UpdateAgentBody {
  name?: string;
  systemPrompt?: string;
  voiceType?: 'male' | 'female';
  llmPreferences?: any;
  tokenLimit?: number;
  contextWindowStrategy?: 'condense' | 'truncate';
}

// Validation schemas
const createAgentSchema = Joi.object({
  name: Joi.string().required(),
  systemPrompt: Joi.string().allow(''),
  voiceType: Joi.string().valid('male', 'female').default('female'),
  llmPreferences: Joi.object().default({ model: 'grok' }),
  tokenLimit: Joi.number().integer().min(1000).max(128000).default(4096),
  contextWindowStrategy: Joi.string().valid('condense', 'truncate').default('condense')
});

const updateAgentSchema = Joi.object({
  name: Joi.string(),
  systemPrompt: Joi.string().allow(''),
  voiceType: Joi.string().valid('male', 'female'),
  llmPreferences: Joi.object(),
  tokenLimit: Joi.number().integer().min(1000).max(128000),
  contextWindowStrategy: Joi.string().valid('condense', 'truncate')
});

// Get all agents for a user
router.get('/', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const userId = req.userId; // Get from authenticated request

    if (!userId) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const agents = await prisma.agent.findMany({
      where: {
        userId: userId,
        tenantId: req.tenantId // Ensure tenant isolation
      },
      include: {
        _count: {
          select: { documents: true }
        }
      }
    });

    res.json(agents);
  } catch (error) {
    console.error('Error fetching agents:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get agent by ID
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    const agent = await prisma.agent.findFirst({
      where: {
        id: id,
        tenantId: req.tenantId // Ensure tenant isolation
      },
      include: {
        documents: {
          select: {
            id: true,
            url: true,
            s3Path: true,
            status: true,
            title: true,
            createdAt: true
          }
        },
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
    console.error('Error fetching agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create new agent
router.post('/', async (req: Request, res: Response) => {
  try {
    const { error, value } = createAgentSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { userId, ...agentData } = value as CreateAgentBody & { userId: string };

    if (!userId) {
      return res.status(400).json({ error: 'User ID required' });
    }

    // Verify user belongs to tenant
    const user = await prisma.user.findFirst({
      where: {
        id: userId,
        tenantId: req.tenantId
      }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found or does not belong to tenant' });
    }

    const agent = await prisma.agent.create({
      data: {
        ...agentData,
        tenantId: req.tenantId,
        userId: userId
      }
    });

    res.status(201).json(agent);
  } catch (error) {
    console.error('Error creating agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update agent
router.put('/:id', async (req: Request, res: Response) => {
  try {
    const { error, value } = updateAgentSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    // Verify agent belongs to tenant
    const existingAgent = await prisma.agent.findFirst({
      where: {
        id: id,
        tenantId: req.tenantId
      }
    });

    if (!existingAgent) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    const agent = await prisma.agent.update({
      where: { id: id },
      data: value as UpdateAgentBody
    });

    res.json(agent);
  } catch (error) {
    console.error('Error updating agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete agent
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    // Verify agent belongs to tenant
    const existingAgent = await prisma.agent.findFirst({
      where: {
        id: id,
        tenantId: req.tenantId
      }
    });

    if (!existingAgent) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    await prisma.agent.delete({
      where: { id: id }
    });

    res.status(204).send();
  } catch (error) {
    console.error('Error deleting agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;