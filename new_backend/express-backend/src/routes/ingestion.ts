import express, { Request, Response, NextFunction, Router } from 'express';
import Joi from 'joi';
import axios from 'axios';
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

// Interfaces
interface StartIngestionBody {
  agentId: string;
  urls?: string[];
  s3Urls?: string[];
}

// Validation schemas
const startIngestionSchema = Joi.object({
  agentId: Joi.string().required(),
  urls: Joi.array().items(Joi.string().uri()).default([]),
  s3Urls: Joi.array().items(Joi.string()).default([])
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

// Start document ingestion
router.post('/start', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const { error, value } = startIngestionSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { agentId, urls, s3Urls } = value as StartIngestionBody;

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

    // Create documents in database
    const documents = [];
    for (const url of urls || []) {
      const doc = await prisma.document.create({
        data: {
          url: url,
          agentId: agentId,
          tenantId: req.user.tenantId,
          status: 'pending'
        }
      });
      documents.push(doc);
    }

    for (const s3Url of s3Urls || []) {
      const doc = await prisma.document.create({
        data: {
          s3Path: s3Url,
          agentId: agentId,
          tenantId: req.user.tenantId,
          status: 'pending'
        }
      });
      documents.push(doc);
    }

    // Trigger ingestion service
    const ingestionServiceUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    const ingestionResponse = await axios.post(`${ingestionServiceUrl}/ingest`, {
      tenantId: req.tenantId,
      agentId: agentId,
      urls: urls,
      s3_urls: s3Urls
    });

    res.json({
      jobId: ingestionResponse.data.job_id,
      documents: documents,
      status: 'processing'
    });
  } catch (error) {
    console.error('Error starting ingestion:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Check ingestion status
router.get('/status/:jobId', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const { jobId } = req.params;

    const ingestionServiceUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    const response = await axios.get(`${ingestionServiceUrl}/status/${jobId}`);

    res.json(response.data);
  } catch (error) {
    console.error('Error checking ingestion status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get ingestion jobs for agent
router.get('/jobs', validateTenantAccess, async (req: Request, res: Response) => {
  try {
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
    const pattern = `job:${req.tenantId}:${agentId}:*`;
    const keys = await redis.keys(pattern);

    const jobs = [];
    for (const key of keys) {
      const jobId = key.split(':')[3];
      const status = await redis.get(`job:${jobId}`);
      const progress = await redis.get(`job:${jobId}:progress`);

      jobs.push({
        jobId: jobId,
        status: status,
        progress: progress ? parseInt(progress) : 0
      });
    }

    res.json(jobs);
  } catch (error) {
    console.error('Error fetching ingestion jobs:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;