import express, { Request, Response, NextFunction, Router } from 'express';
import Joi from 'joi';
import axios from 'axios';
import multer from 'multer';
import { PrismaClient } from '@prisma/client';
import MinioService from '../services/minioService';

const router: Router = express.Router();

// Configure multer for file uploads
const upload = multer({
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    // Allow common document types
    const allowedTypes = [
      'application/pdf',
      'text/plain',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/csv',
      'application/json'
    ];
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  }
});

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

  // Verify tenant exists and is active
  const prisma = req.app.get('prisma') as PrismaClient;
  prisma.tenant.findUnique({
    where: { id: tenantId, isActive: true }
  }).then(tenant => {
    if (!tenant) {
      return res.status(403).json({ error: 'Invalid or inactive tenant' });
    }
    req.tenantId = tenantId;
    next();
  });
}

// Get all documents for an agent
router.get('/', async (req: Request, res: Response) => {
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
        tenantId: req.tenantId
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
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    const document = await prisma.document.findFirst({
      where: {
        id: id,
        tenantId: req.tenantId
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
router.post('/', async (req: Request, res: Response) => {
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
        tenantId: req.tenantId
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const document = await prisma.document.create({
      data: {
        url: url,
        agentId: agentId,
        tenantId: req.tenantId,
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
router.put('/:id', async (req: Request, res: Response) => {
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
        tenantId: req.tenantId
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
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { id } = req.params;

    // Verify document belongs to tenant
    const document = await prisma.document.findFirst({
      where: {
        id: id,
        tenantId: req.tenantId
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

// Upload document file
router.post('/upload', upload.single('file'), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const agentId = req.body.agentId;
    if (!agentId) {
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

    // Upload file to MinIO
    const fileName = `${Date.now()}_${req.file.originalname}`;
    const s3Path = await MinioService.uploadBuffer(
      req.tenantId,
      req.file.buffer,
      fileName,
      req.file.mimetype
    );

    // Create document record
    const document = await prisma.document.create({
      data: {
        s3Path: s3Path,
        agentId: agentId,
        tenantId: req.tenantId,
        status: 'pending',
        title: req.file.originalname
      }
    });

    // Trigger ingestion service
    const ingestionServiceUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    try {
      await axios.post(`${ingestionServiceUrl}/ingest`, {
        tenantId: req.tenantId,
        agentId: agentId,
        s3_urls: [s3Path]
      });
    } catch (ingestionError) {
      console.warn('Failed to trigger ingestion service:', ingestionError);
      // Don't fail the upload if ingestion fails
    }

    res.status(201).json({
      document: {
        id: document.id,
        s3Path: document.s3Path,
        title: document.title,
        status: document.status,
        createdAt: document.createdAt
      }
    });
  } catch (error) {
    console.error('Error uploading document:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;