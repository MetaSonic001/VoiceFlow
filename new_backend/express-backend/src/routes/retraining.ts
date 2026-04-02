import express, { Request, Response, Router } from 'express';
import { PrismaClient } from '@prisma/client';
import Joi from 'joi';
import { processFlaggedCallLogs } from '../services/retrainingService';

const router: Router = express.Router();

// ─── GET /api/retraining ──────────────────────────────────────────────────────
// List retraining examples for the tenant (with pagination & filtering).
router.get('/', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenantId = req.tenantId;

    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.min(200, Math.max(1, parseInt(req.query.limit as string) || 50));
    const skip = (page - 1) * limit;

    const where: any = { tenantId };
    if (req.query.status) where.status = req.query.status;
    if (req.query.agentId) where.agentId = req.query.agentId;

    const [examples, total] = await Promise.all([
      prisma.retrainingExample.findMany({
        where,
        skip,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          agent: { select: { id: true, name: true } },
          callLog: { select: { id: true, startedAt: true, rating: true } },
        },
      }),
      prisma.retrainingExample.count({ where }),
    ]);

    res.json({ examples, total, page, limit, pages: Math.ceil(total / limit) });
  } catch (error) {
    console.error('Error fetching retraining examples:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── GET /api/retraining/stats ────────────────────────────────────────────────
// Quick counts for the dashboard badge / overview.
router.get('/stats', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenantId = req.tenantId;

    const [pending, approved, rejected, flaggedNotProcessed] = await Promise.all([
      prisma.retrainingExample.count({ where: { tenantId, status: 'pending' } }),
      prisma.retrainingExample.count({ where: { tenantId, status: 'approved' } }),
      prisma.retrainingExample.count({ where: { tenantId, status: 'rejected' } }),
      prisma.callLog.count({ where: { tenantId, flaggedForRetraining: true, retrained: false } }),
    ]);

    res.json({ pending, approved, rejected, flaggedNotProcessed });
  } catch (error) {
    console.error('Error fetching retraining stats:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── PATCH /api/retraining/:id ────────────────────────────────────────────────
// Edit the ideal response and/or change status (approve / reject).
const updateSchema = Joi.object({
  idealResponse: Joi.string().max(5000).optional(),
  status: Joi.string().valid('pending', 'approved', 'rejected').optional(),
}).min(1);

router.patch('/:id', async (req: Request, res: Response) => {
  const { error, value } = updateSchema.validate(req.body);
  if (error) return res.status(400).json({ error: error.details[0].message });

  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const example = await prisma.retrainingExample.findUnique({
      where: { id: req.params.id },
    });
    if (!example) return res.status(404).json({ error: 'Example not found' });
    if (example.tenantId !== req.tenantId) return res.status(403).json({ error: 'Forbidden' });

    const data: any = {};
    if (value.idealResponse !== undefined) data.idealResponse = value.idealResponse;
    if (value.status !== undefined) {
      data.status = value.status;
      if (value.status === 'approved') {
        data.approvedAt = new Date();
        data.approvedBy = req.userId;
      }
    }

    const updated = await prisma.retrainingExample.update({
      where: { id: req.params.id },
      data,
    });

    res.json(updated);
  } catch (error) {
    console.error('Error updating retraining example:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── DELETE /api/retraining/:id ───────────────────────────────────────────────
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const example = await prisma.retrainingExample.findUnique({
      where: { id: req.params.id },
    });
    if (!example) return res.status(404).json({ error: 'Example not found' });
    if (example.tenantId !== req.tenantId) return res.status(403).json({ error: 'Forbidden' });

    await prisma.retrainingExample.delete({ where: { id: req.params.id } });
    res.json({ deleted: true });
  } catch (error) {
    console.error('Error deleting retraining example:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── POST /api/retraining/process ─────────────────────────────────────────────
// Manually trigger the retraining pipeline (normally runs nightly).
router.post('/process', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const count = await processFlaggedCallLogs(prisma);
    res.json({ processed: true, examplesCreated: count });
  } catch (error) {
    console.error('Error running retraining pipeline:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
