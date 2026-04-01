import express, { Request, Response, Router } from 'express';
import Joi from 'joi';
import { PrismaClient } from '@prisma/client';

const router: Router = express.Router();

// ── Validation ────────────────────────────────────────────────────────────────

const policyRuleSchema = Joi.object({
  type: Joi.string().valid('allow', 'restrict', 'require').required(),
  target: Joi.string().valid('topic', 'documentSource', 'documentTag').required(),
  value: Joi.string().required(),
});

const createBrandSchema = Joi.object({
  name: Joi.string().min(1).max(200).required(),
  brandVoice: Joi.string().max(2000).allow('', null).optional(),
  allowedTopics: Joi.array().items(Joi.string()).optional(),
  restrictedTopics: Joi.array().items(Joi.string()).optional(),
  policyRules: Joi.array().items(policyRuleSchema).optional(),
});

const updateBrandSchema = Joi.object({
  name: Joi.string().min(1).max(200).optional(),
  brandVoice: Joi.string().max(2000).allow('', null).optional(),
  allowedTopics: Joi.array().items(Joi.string()).optional(),
  restrictedTopics: Joi.array().items(Joi.string()).optional(),
  policyRules: Joi.array().items(policyRuleSchema).optional(),
});

// ── GET /api/brands ───────────────────────────────────────────────────────────
// List all brands for the authenticated tenant.
router.get('/', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const brands = await prisma.brand.findMany({
      where: { tenantId: req.tenantId },
      include: {
        _count: { select: { agents: true } },
      },
      orderBy: { createdAt: 'desc' },
    });
    res.json(brands);
  } catch (error) {
    console.error('Error fetching brands:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── GET /api/brands/:id ───────────────────────────────────────────────────────
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const brand = await prisma.brand.findFirst({
      where: { id: req.params.id, tenantId: req.tenantId },
      include: {
        agents: { select: { id: true, name: true, status: true } },
      },
    });
    if (!brand) return res.status(404).json({ error: 'Brand not found' });
    res.json(brand);
  } catch (error) {
    console.error('Error fetching brand:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── POST /api/brands ──────────────────────────────────────────────────────────
router.post('/', async (req: Request, res: Response) => {
  const { error, value } = createBrandSchema.validate(req.body);
  if (error) return res.status(400).json({ error: error.details[0].message });

  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const brand = await prisma.brand.create({
      data: {
        tenantId: req.tenantId,
        name: value.name,
        brandVoice: value.brandVoice ?? null,
        allowedTopics: value.allowedTopics ?? [],
        restrictedTopics: value.restrictedTopics ?? [],
        policyRules: value.policyRules ?? [],
      },
    });
    res.status(201).json(brand);
  } catch (error) {
    console.error('Error creating brand:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── PUT /api/brands/:id ───────────────────────────────────────────────────────
router.put('/:id', async (req: Request, res: Response) => {
  const { error, value } = updateBrandSchema.validate(req.body);
  if (error) return res.status(400).json({ error: error.details[0].message });

  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const existing = await prisma.brand.findFirst({
      where: { id: req.params.id, tenantId: req.tenantId },
    });
    if (!existing) return res.status(404).json({ error: 'Brand not found' });

    const brand = await prisma.brand.update({
      where: { id: req.params.id },
      data: value,
    });
    res.json(brand);
  } catch (error) {
    console.error('Error updating brand:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ── DELETE /api/brands/:id ────────────────────────────────────────────────────
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    const existing = await prisma.brand.findFirst({
      where: { id: req.params.id, tenantId: req.tenantId },
    });
    if (!existing) return res.status(404).json({ error: 'Brand not found' });

    await prisma.brand.delete({ where: { id: req.params.id } });
    res.json({ deleted: true });
  } catch (error) {
    console.error('Error deleting brand:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
