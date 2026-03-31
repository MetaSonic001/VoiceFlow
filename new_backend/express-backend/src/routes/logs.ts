import express, { Request, Response, Router } from 'express';
import { PrismaClient } from '@prisma/client';
import Joi from 'joi';

const router: Router = express.Router();

// ─── GET /api/logs ────────────────────────────────────────────────────────────
// Returns paginated call logs for the authenticated tenant.
// Query params: agentId, from, to (ISO strings), page, limit
router.get('/', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenantId = req.tenantId;

    const page  = Math.max(1, parseInt(req.query.page  as string) || 1);
    const limit = Math.min(200, Math.max(1, parseInt(req.query.limit as string) || 50));
    const skip  = (page - 1) * limit;

    const where: any = { tenantId };

    if (req.query.agentId) {
      where.agentId = req.query.agentId as string;
    }
    if (req.query.from || req.query.to) {
      where.startedAt = {};
      if (req.query.from) where.startedAt.gte = new Date(req.query.from as string);
      if (req.query.to)   where.startedAt.lte = new Date(req.query.to   as string);
    }

    const [logs, total] = await Promise.all([
      prisma.callLog.findMany({
        where,
        skip,
        take: limit,
        orderBy: { startedAt: 'desc' },
        include: {
          agent: {
            select: { id: true, name: true },
          },
        },
      }),
      prisma.callLog.count({ where }),
    ]);

    res.json({ logs, total, page, limit, pages: Math.ceil(total / limit) });
  } catch (error) {
    console.error('Error fetching call logs:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── PATCH /api/logs/:id/rating ───────────────────────────────────────────────
// Set thumbs-up (1) or thumbs-down (-1) rating + optional notes on a log.
const ratingSchema = Joi.object({
  rating: Joi.number().valid(1, -1).required(),
  notes:  Joi.string().max(2000).allow('', null).optional(),
});

router.patch('/:id/rating', async (req: Request, res: Response) => {
  const { error, value } = ratingSchema.validate(req.body);
  if (error) return res.status(400).json({ error: error.details[0].message });

  try {
    const prisma: PrismaClient = req.app.get('prisma');

    // Verify the log belongs to this tenant before updating
    const log = await prisma.callLog.findUnique({ where: { id: req.params.id } });
    if (!log)                        return res.status(404).json({ error: 'Log not found' });
    if (log.tenantId !== req.tenantId) return res.status(403).json({ error: 'Forbidden' });

    const updated = await prisma.callLog.update({
      where: { id: req.params.id },
      data: {
        rating:      value.rating,
        ratingNotes: value.notes ?? null,
      },
    });

    res.json(updated);
  } catch (error) {
    console.error('Error updating call log rating:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── POST /api/logs/:id/flag ──────────────────────────────────────────────────
// Mark a log as flagged for retraining.
router.post('/:id/flag', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const log = await prisma.callLog.findUnique({ where: { id: req.params.id } });
    if (!log)                        return res.status(404).json({ error: 'Log not found' });
    if (log.tenantId !== req.tenantId) return res.status(403).json({ error: 'Forbidden' });

    const updated = await prisma.callLog.update({
      where: { id: req.params.id },
      data: { flaggedForRetraining: true },
    });

    res.json(updated);
  } catch (error) {
    console.error('Error flagging call log:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
