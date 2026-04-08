import express, { Request, Response, NextFunction, Router } from 'express';
import { PrismaClient } from '@prisma/client';
import multer from 'multer';
import axios from 'axios';
import { provisionAgentNumber, deprovisionAgentNumber } from '../services/twilioProvisioningService';

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

// ─── Company search endpoint ──────────────────────────────────────────────────
// Proxies to Clearbit Autocomplete (free, no auth) to search any real company.
// Falls back to empty array if Clearbit is unreachable.
router.get('/company-search', async (req: Request, res: Response) => {
  const q = ((req.query.q as string) || '').trim();
  if (!q || q.length < 1) {
    return res.json({ companies: [] });
  }
  try {
    const response = await axios.get(
      `https://autocomplete.clearbit.com/v1/companies/suggest?query=${encodeURIComponent(q)}`,
      { timeout: 5000 }
    );
    const companies = (response.data || []).slice(0, 10).map((item: any) => ({
      id:          item.domain || item.name.toLowerCase().replace(/\s+/g, '-'),
      name:        item.name,
      domain:      item.domain || '',
      industry:    '',        // Clearbit autocomplete doesn't expose industry
      description: item.domain || '',
    }));
    res.json({ companies });
  } catch (err) {
    console.error('Clearbit search failed:', err);
    res.json({ companies: [] });
  }
});

// ─── Company profile setup ────────────────────────────────────────────────────
// GET: return existing company profile from tenant settings
router.get('/company', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const settings = (tenant?.settings as any) || {};
    res.json({
      company_name: settings.companyName || null,
      industry: settings.industry || null,
      use_case: settings.useCase || null,
      website_url: settings.websiteUrl || null,
      description: settings.description || null,
    });
  } catch (error) {
    console.error('Error fetching company profile:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST: saves company metadata to tenant.settings AND triggers a background scrape
// of the company website so that content lands in the vector store immediately.
router.post('/company', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { company_name, industry, use_case, website_url, description } = req.body;

    // Persist to Postgres tenant record
    await prisma.tenant.update({
      where: { id: req.tenantId },
      data: {
        settings: {
          companyName: company_name,
          industry: industry,
          useCase: use_case,
          websiteUrl: website_url || null,
          description: description || null,
        },
      },
    });

    // If a website URL was provided, kick off a background ingestion job so
    // company knowledge is available right away for RAG.
    let scrapeJobId: string | null = null;
    if (website_url) {
      try {
        const ingestionUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
        const scrapeRes = await axios.post(`${ingestionUrl}/ingest/company`, {
          tenantId: req.tenantId,
          website_url,
          company_name: company_name || '',
          company_description: description || undefined,
          industry: industry || undefined,
          use_case: use_case || undefined,
        });
        scrapeJobId = scrapeRes.data?.job_id || null;
        console.log(`Company scrape job started: ${scrapeJobId} for tenant ${req.tenantId}`);
      } catch (scrapeErr) {
        // Non-fatal: log but don't block the onboarding response
        console.error('Failed to trigger company scrape:', scrapeErr);
      }
    }

    res.json({ success: true, scrapeJobId });
  } catch (error) {
    console.error('Error saving company profile:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── Proxy: ingestion job status ─────────────────────────────────────────────
// Frontend polls this to show scraping progress without talking directly to FastAPI.
router.get('/scrape-status/:jobId', async (req: Request, res: Response) => {
  try {
    const ingestionUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    const response = await axios.get(`${ingestionUrl}/status/${req.params.jobId}`);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching scrape status:', error);
    res.status(500).json({ error: 'Failed to fetch scrape status' });
  }
});

// ─── Proxy: company knowledge list ───────────────────────────────────────────
// Returns chunks from ChromaDB that belong to the company_profile source.
router.get('/company-knowledge', async (req: Request, res: Response) => {
  try {
    const ingestionUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    const response = await axios.get(
      `${ingestionUrl}/knowledge/company/${req.tenantId}`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching company knowledge:', error);
    res.status(500).json({ error: 'Failed to fetch company knowledge' });
  }
});

// ─── Proxy: delete a knowledge chunk ─────────────────────────────────────────
router.delete('/company-knowledge/:chunkId', async (req: Request, res: Response) => {
  try {
    const ingestionUrl = process.env.FASTAPI_URL || 'http://localhost:8001';
    await axios.delete(
      `${ingestionUrl}/knowledge/${req.tenantId}/${req.params.chunkId}`
    );
    res.json({ deleted: true });
  } catch (error) {
    console.error('Error deleting knowledge chunk:', error);
    res.status(500).json({ error: 'Failed to delete chunk' });
  }
});

// Agent creation
router.post('/agent', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { name, role, templateId, description, channels, brandId } = req.body;

    // If brandId provided, verify it belongs to the same tenant
    if (brandId) {
      const brand = await prisma.brand.findFirst({ where: { id: brandId, tenantId: req.tenantId } });
      if (!brand) {
        return res.status(400).json({ error: 'Brand not found or does not belong to this tenant' });
      }
    }

    // Create the agent with optional template and brand reference
    const agent = await prisma.agent.create({
      data: {
        name,
        description: description || role || undefined,
        templateId: templateId || undefined,
        brandId: brandId || undefined,
        channels: channels || undefined,
        userId: req.userId,
        tenantId: req.tenantId,
      },
    });

    // Create the corresponding agent configuration (non-fatal if schema differs)
    try {
      const tenantSettings = (
        await prisma.tenant.findUnique({ where: { id: req.tenantId } })
      )?.settings as Record<string, any> | null;

      await prisma.agentConfiguration.create({
        data: {
          agentId: agent.id,
          templateId: templateId || undefined,
          agentName: name,
          agentRole: role || undefined,
          agentDescription: description || undefined,
          communicationChannels: channels || undefined,
          companyName: tenantSettings?.companyName || undefined,
          industry: tenantSettings?.industry || undefined,
          primaryUseCase: tenantSettings?.useCase || undefined,
        },
      });
    } catch (configErr) {
      console.warn('Failed to create agent configuration (non-fatal):', configErr);
    }

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

// Voice configuration — save voiceId to agent configuration
router.post('/voice', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { voice, tone, language, personality } = req.body;

    // Find the tenant's most recent agent and update its configuration
    const agent = await prisma.agent.findFirst({
      where: { tenantId: req.tenantId },
      orderBy: { createdAt: 'desc' },
    });

    if (agent) {
      await prisma.agentConfiguration.upsert({
        where: { agentId: agent.id },
        update: {
          voiceId: voice || undefined,
          responseTone: tone || undefined,
          preferredResponseStyle: personality || undefined,
        },
        create: {
          agentId: agent.id,
          voiceId: voice || undefined,
          responseTone: tone || undefined,
          preferredResponseStyle: personality || undefined,
        },
      });
    }

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
    const prisma: PrismaClient = req.app.get('prisma');
    const {
      agent_name, agent_role, agent_description,
      personality_traits, communication_channels,
      preferred_response_style, response_tone, voice_id,
      company_name, industry, primary_use_case,
    } = req.body;

    // Find the tenant's most recent agent
    const agent = await prisma.agent.findFirst({
      where: { tenantId: req.tenantId },
      orderBy: { createdAt: 'desc' },
    });

    if (agent) {
      await prisma.agentConfiguration.upsert({
        where: { agentId: agent.id },
        update: {
          agentName: agent_name || undefined,
          agentRole: agent_role || undefined,
          agentDescription: agent_description || undefined,
          personalityTraits: personality_traits || undefined,
          communicationChannels: communication_channels || undefined,
          preferredResponseStyle: preferred_response_style || undefined,
          responseTone: response_tone || undefined,
          voiceId: voice_id || undefined,
          companyName: company_name || undefined,
          industry: industry || undefined,
          primaryUseCase: primary_use_case || undefined,
        },
        create: {
          agentId: agent.id,
          agentName: agent_name || undefined,
          agentRole: agent_role || undefined,
          agentDescription: agent_description || undefined,
          personalityTraits: personality_traits || undefined,
          communicationChannels: communication_channels || undefined,
          preferredResponseStyle: preferred_response_style || undefined,
          responseTone: response_tone || undefined,
          voiceId: voice_id || undefined,
          companyName: company_name || undefined,
          industry: industry || undefined,
          primaryUseCase: primary_use_case || undefined,
        },
      });
    }

    res.json({
      success: true,
      message: 'Agent configured successfully',
      agent_id: agent?.id || 'unknown',
      chroma_collection: `collection_${req.tenantId}`,
    });
  } catch (error) {
    console.error('Error configuring agent:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Deploy agent — provision a real Twilio phone number
router.post('/deploy', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { agent_id, country_code } = req.body;

    if (!agent_id) {
      return res.status(400).json({ error: 'agent_id is required' });
    }

    // Verify the agent belongs to this tenant
    const agent = await prisma.agent.findFirst({
      where: { id: agent_id, tenantId: req.tenantId },
    });
    if (!agent) {
      return res.status(404).json({ error: 'Agent not found' });
    }

    // If the agent already has a number, return it
    if (agent.phoneNumber) {
      return res.json({ success: true, phone_number: agent.phoneNumber, already_provisioned: true });
    }

    // Pre-flight: ensure tenant has Twilio credentials configured
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const tenantSettings = (tenant?.settings as Record<string, any>) || {};
    if (!tenantSettings.twilioAccountSid || !tenantSettings.twilioAuthToken) {
      return res.status(400).json({
        error: 'Twilio credentials not configured. Please add your Twilio Account SID and Auth Token in Settings \u2192 Integrations before deploying.',
        code: 'TWILIO_NOT_CONFIGURED',
      });
    }

    const phoneNumber = await provisionAgentNumber(
      prisma,
      agent_id,
      req.tenantId,
      country_code || 'US',
    );

    // Activate the agent
    await prisma.agent.update({
      where: { id: agent_id },
      data: { status: 'active' },
    });

    res.json({ success: true, phone_number: phoneNumber });
  } catch (error: any) {
    console.error('Error deploying agent:', error);
    res.status(500).json({ error: error?.message || 'Failed to deploy agent' });
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