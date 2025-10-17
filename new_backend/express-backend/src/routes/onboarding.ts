import express, { Request, Response, NextFunction, Router } from 'express';
import { PrismaClient } from '@prisma/client';
import multer from 'multer';
import axios from 'axios';

const router: Router = express.Router();
const upload = multer({ dest: 'uploads/' });

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
    }
  }
}

// Company profile setup
router.post('/company', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { company_name, industry, use_case } = req.body;

    // For now, just store in tenant settings
    await prisma.tenant.update({
      where: { id: req.tenantId },
      data: {
        settings: {
          companyName: company_name,
          industry: industry,
          useCase: use_case,
        },
      },
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Error saving company profile:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Agent creation
router.post('/agent', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { name } = req.body;

    const agent = await prisma.agent.create({
      data: {
        name,
        userId: req.userId,
        tenantId: req.tenantId,
      },
    });

    res.json({ agent_id: agent.id });
  } catch (error) {
    console.error('Error creating agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Knowledge upload
router.post('/knowledge', upload.array('files'), async (req: Request, res: Response) => {
  try {
    const files = req.files as Express.Multer.File[];
    const { websites, faq_text } = req.body;

    // Forward to ingestion service
    const ingestionUrl = process.env.FASTAPI_URL || 'http://localhost:8001';

    const formData = new FormData();
    files?.forEach((file) => {
      // Convert multer file to blob for FormData
      const fs = require('fs');
      const blob = new Blob([fs.readFileSync(file.path)], { type: file.mimetype });
      formData.append('files', blob, file.originalname);
    });

    if (websites) {
      formData.append('websites', JSON.stringify(websites));
    }

    if (faq_text) {
      formData.append('faq_text', faq_text);
    }

    formData.append('tenant_id', req.tenantId);
    formData.append('user_id', req.userId);

    const response = await axios.post(`${ingestionUrl}/ingest`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    res.json({ success: true, jobId: response.data.job_id });
  } catch (error) {
    console.error('Error uploading knowledge:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Voice configuration
router.post('/voice', async (req: Request, res: Response) => {
  try {
    // For now, just return success
    res.json({ success: true });
  } catch (error) {
    console.error('Error configuring voice:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Channel setup
router.post('/channels', async (req: Request, res: Response) => {
  try {
    // For now, just return success
    res.json({ success: true });
  } catch (error) {
    console.error('Error setting up channels:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Agent configuration
router.post('/agent-config', async (req: Request, res: Response) => {
  try {
    // For now, just return success
    res.json({
      success: true,
      message: 'Agent configured successfully',
      agent_id: 'temp_id',
      chroma_collection: `collection_${req.tenantId}`,
    });
  } catch (error) {
    console.error('Error configuring agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Deploy agent
router.post('/deploy', async (req: Request, res: Response) => {
  try {
    // For now, just return success
    res.json({ success: true, phone_number: '+18283838255' });
  } catch (error) {
    console.error('Error deploying agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get deployment status
router.get('/status', async (req: Request, res: Response) => {
  try {
    // Return mock status
    res.json({
      status: 'ready',
      message: 'Agent is ready for deployment',
    });
  } catch (error) {
    console.error('Error getting deployment status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Onboarding progress - simplified version without database
let onboardingProgressStore: { [key: string]: any } = {};

router.post('/progress', async (req: Request, res: Response) => {
  try {
    const { agent_id, current_step, data } = req.body;
    const key = req.userId;

    onboardingProgressStore[key] = {
      agent_id,
      current_step,
      data,
      updatedAt: new Date(),
    };

    res.json({
      success: true,
      agent_id,
      current_step,
      data,
    });
  } catch (error) {
    console.error('Error saving onboarding progress:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/progress', async (req: Request, res: Response) => {
  try {
    const key = req.userId;
    const progress = onboardingProgressStore[key];

    if (progress) {
      res.json({
        exists: true,
        agent_id: progress.agent_id,
        current_step: progress.current_step,
        data: progress.data,
      });
    } else {
      res.json({ exists: false });
    }
  } catch (error) {
    console.error('Error getting onboarding progress:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.delete('/progress', async (req: Request, res: Response) => {
  try {
    const key = req.userId;
    delete onboardingProgressStore[key];
    res.json({ deleted: true });
  } catch (error) {
    console.error('Error deleting onboarding progress:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;