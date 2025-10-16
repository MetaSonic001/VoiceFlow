import express, { Request, Response, NextFunction, Router } from 'express';
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

// Pipeline agents
router.post('/pipeline_agents', async (req: Request, res: Response) => {
  try {
    // For now, just return mock response
    const { tenant_id, name, agent_type, agent_id, config } = req.body;

    res.json({
      id: `pipeline_${Date.now()}`,
      name,
      tenant_id,
      agent_type,
      agent_id,
      config,
    });
  } catch (error) {
    console.error('Error creating pipeline agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/pipeline_agents', async (req: Request, res: Response) => {
  try {
    // Return mock pipeline agents
    const mockAgents = [
      {
        id: 'pipeline_1',
        name: 'Customer Support Agent',
        tenant_id: req.tenantId,
        agent_type: 'support',
      }
    ];

    res.json({ pipeline_agents: mockAgents });
  } catch (error) {
    console.error('Error listing pipeline agents:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Pipelines
router.post('/pipelines', async (req: Request, res: Response) => {
  try {
    // For now, just return mock response
    const { tenant_id, name, agent_id, stages } = req.body;

    res.json({
      id: `pipeline_${Date.now()}`,
      name,
      tenant_id,
      agent_id,
      stages,
    });
  } catch (error) {
    console.error('Error creating pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/pipelines', async (req: Request, res: Response) => {
  try {
    // Return mock pipelines
    const mockPipelines = [
      {
        id: 'pipeline_1',
        name: 'Customer Onboarding Pipeline',
        tenant_id: req.tenantId,
        stages: ['welcome', 'qualification', 'setup'],
      }
    ];

    res.json({ pipelines: mockPipelines });
  } catch (error) {
    console.error('Error listing pipelines:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Trigger pipeline
router.post('/pipelines/trigger', async (req: Request, res: Response) => {
  try {
    const { pipeline_id, target_agent_id } = req.body;

    // For now, just return mock response
    res.json({
      status: 'triggered',
      pipeline_id,
      target_agent_id,
      message: 'Pipeline triggered successfully',
    });
  } catch (error) {
    console.error('Error triggering pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;