import express, { Request, Response, NextFunction } from 'express';
import Joi from 'joi';
import axios from 'axios';
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
interface CreateDocumentBody {
  url?: string;
  agentId: string;
}

interface UpdateDocumentBody {
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  title?: string;
  content?: string;
  metadata?: any;
}

// Validation schemas
const createDocumentSchema = Joi.object({
  url: Joi.string().uri().allow(null),
  agentId: Joi.string().required()
});

const updateDocumentSchema = Joi.object({
  status: Joi.string().valid('pending', 'processing', 'completed', 'failed'),
  title: Joi.string().allow(''),
  content: Joi.string().allow(''),
  metadata: Joi.object()
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

// Get all documents for an agent
router.get('/', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { agentId } = req.query;

    if (!agentId || typeof agentId !== 'string') {
      return res.status(400).json({ error: 'Agent ID required' });
    }

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        user: { id: req.tenantId }
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const documents = await prisma.document.findMany({
      where: { agentId: agentId },
      orderBy: { createdAt: 'desc' }
    });

    res.json(documents);
  } catch (error) {
    console.error('Error fetching documents:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get document by ID
router.get('/:id', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    const document = await prisma.document.findFirst({
      where: {
        id: id,
        agent: {
          user: { id: req.tenantId }
        }
      }
    });

    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    res.json(document);
  } catch (error) {
    console.error('Error fetching document:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Create new document (URL-based)
router.post('/', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const { error, value } = createDocumentSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { agentId, url } = value as CreateDocumentBody;

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        user: { id: req.tenantId }
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const document = await prisma.document.create({
      data: {
        url: url,
        agentId: agentId,
        status: 'pending'
      }
    });

    // Trigger ingestion asynchronously
    const ingestionServiceUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    try {
      await axios.post(`${ingestionServiceUrl}/ingest`, {
        tenantId: req.tenantId,
        agentId: agentId,
        urls: url ? [url] : []
      });
    } catch (ingestionError) {
      console.error('Error triggering ingestion:', ingestionError);
      // Don't fail the document creation if ingestion fails
    }

    res.status(201).json(document);
  } catch (error) {
    console.error('Error creating document:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Update document
router.put('/:id', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const { error, value } = updateDocumentSchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    // Verify document belongs to tenant
    const existingDocument = await prisma.document.findFirst({
      where: {
        id: id,
        agent: {
          user: { id: req.tenantId }
        }
      }
    });

    if (!existingDocument) {
      return res.status(404).json({ error: 'Document not found' });
    }

    const document = await prisma.document.update({
      where: { id: id },
      data: value as UpdateDocumentBody
    });

    res.json(document);
  } catch (error) {
    console.error('Error updating document:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Delete document
router.delete('/:id', validateTenantAccess, async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    // Verify document belongs to tenant
    const document = await prisma.document.findFirst({
      where: {
        id: id,
        agent: {
          user: { id: req.tenantId }
        }
      }
    });

    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }

    await prisma.document.delete({
      where: { id: id }
    });

    res.status(204).send();
  } catch (error) {
    console.error('Error deleting document:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;