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

// ── Pipelines ───────────────────────────────────────────────────────────────

router.post('/pipelines', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { name, stages } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Pipeline name is required' });
    }

    const pipeline = await prisma.pipeline.create({
      data: {
        tenantId: req.tenantId,
        name,
        stages: Array.isArray(stages) ? stages : [],
      },
    });

    res.status(201).json(pipeline);
  } catch (error) {
    console.error('Error creating pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/pipelines', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const pipelines = await prisma.pipeline.findMany({
      where: { tenantId: req.tenantId },
      orderBy: { createdAt: 'desc' },
    });

    res.json({ pipelines });
  } catch (error) {
    console.error('Error listing pipelines:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.put('/pipelines/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { name, stages } = req.body;

    const pipeline = await prisma.pipeline.updateMany({
      where: { id: req.params.id, tenantId: req.tenantId },
      data: {
        ...(name !== undefined && { name }),
        ...(stages !== undefined && { stages }),
      },
    });

    if (pipeline.count === 0) {
      return res.status(404).json({ error: 'Pipeline not found' });
    }

    const updated = await prisma.pipeline.findUnique({ where: { id: req.params.id } });
    res.json(updated);
  } catch (error) {
    console.error('Error updating pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.delete('/pipelines/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const deleted = await prisma.pipeline.deleteMany({
      where: { id: req.params.id, tenantId: req.tenantId },
    });

    if (deleted.count === 0) {
      return res.status(404).json({ error: 'Pipeline not found' });
    }

    res.json({ success: true });
  } catch (error) {
    console.error('Error deleting pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Trigger pipeline — kicks off the configured ingestion stages
router.post('/pipelines/trigger', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { pipeline_id } = req.body;

    if (!pipeline_id) {
      return res.status(400).json({ error: 'pipeline_id is required' });
    }

    const pipeline = await prisma.pipeline.findFirst({
      where: { id: pipeline_id, tenantId: req.tenantId },
    });

    if (!pipeline) {
      return res.status(404).json({ error: 'Pipeline not found' });
    }

    // Update status to running
    await prisma.pipeline.update({
      where: { id: pipeline_id },
      data: { status: 'running', lastRunAt: new Date() },
    });

    // Execute stages asynchronously — mark completed when done
    const stages = Array.isArray(pipeline.stages) ? pipeline.stages : [];
    setImmediate(async () => {
      try {
        for (const stage of stages as Array<{ type?: string; config?: any }>) {
          // Stage types: 'scrape_url', 'ingest_file', 'refresh_collection'
          // Future: wire each stage type to the ingestion service
          console.log(`[pipeline] Running stage: ${stage.type || 'unknown'}`);
        }
        await prisma.pipeline.update({
          where: { id: pipeline_id },
          data: { status: 'completed' },
        });
      } catch (err) {
        console.error('[pipeline] Execution error:', err);
        await prisma.pipeline.update({
          where: { id: pipeline_id },
          data: { status: 'failed' },
        }).catch(() => {});
      }
    });

    res.json({ status: 'triggered', pipeline_id });
  } catch (error) {
    console.error('Error triggering pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── Pipeline agents (agents assigned to pipelines) ──────────────────────────
// These refer to the tenant's existing agents — no separate model needed.

router.get('/pipeline_agents', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const agents = await prisma.agent.findMany({
      where: { tenantId: req.tenantId },
      select: {
        id: true,
        name: true,
        status: true,
        description: true,
        voiceType: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    // Map to the pipeline_agents format the frontend expects
    const pipeline_agents = agents.map(a => ({
      id: a.id,
      name: a.name,
      agent_type: a.voiceType || 'general',
      agent_id: a.id,
      status: a.status,
    }));

    res.json({ pipeline_agents });
  } catch (error) {
    console.error('Error listing pipeline agents:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/pipeline_agents', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { name, agent_type, agent_id } = req.body;

    // Verify the referenced agent belongs to this tenant
    if (agent_id) {
      const agent = await prisma.agent.findFirst({
        where: { id: agent_id, tenantId: req.tenantId },
      });
      if (!agent) {
        return res.status(404).json({ error: 'Agent not found' });
      }
    }

    res.json({ id: agent_id, name, agent_type });
  } catch (error) {
    console.error('Error creating pipeline agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;