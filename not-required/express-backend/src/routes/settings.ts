import { Router, Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import axios from 'axios';
import twilio from 'twilio';
import { encryptCredential, decryptCredential } from '../services/credentialsService';
import { invalidateTwilioClientCache, getTenantTwilioCreds } from '../services/twilioClientService';

const router = Router();

// ─── POST /api/settings/twilio ───────────────────────────────────────────────
// Validate and store encrypted Twilio credentials for the tenant.

router.post('/twilio', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { accountSid, authToken } = req.body;

    if (!accountSid || !authToken) {
      return res.status(400).json({ error: 'accountSid and authToken are required.' });
    }

    // Validate credentials by making a test call to the Twilio API
    try {
      const testClient = twilio(accountSid, authToken);
      await testClient.api.accounts(accountSid).fetch();
    } catch (twilioErr: any) {
      const msg =
        twilioErr?.status === 401
          ? 'Invalid credentials — check your Account SID and Auth Token.'
          : `Twilio API error: ${twilioErr?.message || 'Unknown error'}`;
      return res.status(400).json({ error: msg });
    }

    // Encrypt both values
    const encryptedSid = encryptCredential(accountSid);
    const encryptedToken = encryptCredential(authToken);

    // Merge into tenant.settings (preserve existing settings)
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const existingSettings = (tenant?.settings as Record<string, any>) || {};

    await prisma.tenant.update({
      where: { id: req.tenantId },
      data: {
        settings: {
          ...existingSettings,
          twilioAccountSid: encryptedSid,
          twilioAuthToken: encryptedToken,
          twilioCredentialsVerified: true,
          twilioCredentialsUpdatedAt: new Date().toISOString(),
        },
      },
    });

    // Invalidate the cached Twilio client so the next call picks up new creds
    invalidateTwilioClientCache(req.tenantId);

    res.json({
      success: true,
      message: 'Twilio credentials verified and saved.',
      accountSid, // Return the plain SID (not secret)
    });
  } catch (error) {
    console.error('[settings/twilio] Error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── GET /api/settings/twilio ────────────────────────────────────────────────
// Return credential status (never expose raw auth token).

router.get('/twilio', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const settings = (tenant?.settings as Record<string, any>) || {};

    // Try to decrypt the SID to return it in plain form
    let accountSid: string | null = null;
    if (settings.twilioAccountSid) {
      try {
        accountSid = decryptCredential(settings.twilioAccountSid);
      } catch {
        accountSid = null; // corrupt or missing key
      }
    }

    res.json({
      configured: !!accountSid && !!settings.twilioAuthToken,
      accountSid,
      hasAuthToken: !!settings.twilioAuthToken,
      credentialsVerified: !!settings.twilioCredentialsVerified,
      updatedAt: settings.twilioCredentialsUpdatedAt || null,
    });
  } catch (error) {
    console.error('[settings/twilio GET] Error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── DELETE /api/settings/twilio ─────────────────────────────────────────────
// Remove stored Twilio credentials.

router.delete('/twilio', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const existingSettings = (tenant?.settings as Record<string, any>) || {};

    // Remove Twilio fields
    const { twilioAccountSid, twilioAuthToken, twilioCredentialsVerified, twilioCredentialsUpdatedAt, ...rest } = existingSettings;

    await prisma.tenant.update({
      where: { id: req.tenantId },
      data: { settings: rest },
    });

    invalidateTwilioClientCache(req.tenantId);

    res.json({ success: true, message: 'Twilio credentials removed.' });
  } catch (error) {
    console.error('[settings/twilio DELETE] Error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// Groq Cloud API Key (per-tenant)
// ═══════════════════════════════════════════════════════════════════════════

/** Available Groq production models exposed to tenants. */
const GROQ_PRODUCTION_MODELS = [
  {
    id: 'llama-3.3-70b-versatile',
    name: 'Meta Llama 3.3 70B',
    speed: '280 T/sec',
    contextWindow: 131072,
    maxCompletionTokens: 32768,
    description: 'Best quality — large 70B model, great for complex reasoning and detailed responses.',
  },
  {
    id: 'llama-3.1-8b-instant',
    name: 'Meta Llama 3.1 8B',
    speed: '560 T/sec',
    contextWindow: 131072,
    maxCompletionTokens: 131072,
    description: 'Fastest text model — ideal for simple queries and high-throughput use cases.',
  },
  {
    id: 'openai/gpt-oss-120b',
    name: 'OpenAI GPT OSS 120B',
    speed: '500 T/sec',
    contextWindow: 131072,
    maxCompletionTokens: 65536,
    description: 'Large open-source GPT model — balanced speed and quality.',
  },
  {
    id: 'openai/gpt-oss-20b',
    name: 'OpenAI GPT OSS 20B',
    speed: '1000 T/sec',
    contextWindow: 131072,
    maxCompletionTokens: 65536,
    description: 'Ultra-fast GPT model — best throughput for lightweight tasks.',
  },
];

// ─── GET /api/settings/groq/models ───────────────────────────────────────────
// Return the list of available Groq production models.

router.get('/groq/models', (_req: Request, res: Response) => {
  res.json({ models: GROQ_PRODUCTION_MODELS });
});

// ─── POST /api/settings/groq ─────────────────────────────────────────────────
// Validate and store an encrypted Groq Cloud API key for the tenant.

router.post('/groq', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { apiKey } = req.body;

    if (!apiKey || typeof apiKey !== 'string' || !apiKey.startsWith('gsk_')) {
      return res.status(400).json({
        error: 'A valid Groq API key is required (starts with gsk_).',
      });
    }

    // Validate by making a lightweight test call to the Groq API
    try {
      await axios.get('https://api.groq.com/openai/v1/models', {
        headers: { Authorization: `Bearer ${apiKey}` },
        timeout: 10000,
      });
    } catch (groqErr: any) {
      const status = groqErr?.response?.status;
      const msg =
        status === 401
          ? 'Invalid API key — check your Groq Cloud key.'
          : `Groq API error: ${groqErr?.message || 'Unknown error'}`;
      return res.status(400).json({ error: msg });
    }

    // Encrypt and store
    const encryptedKey = encryptCredential(apiKey);

    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const existingSettings = (tenant?.settings as Record<string, any>) || {};

    await prisma.tenant.update({
      where: { id: req.tenantId },
      data: {
        settings: {
          ...existingSettings,
          groqApiKey: encryptedKey,
          groqKeyVerified: true,
          groqKeyUpdatedAt: new Date().toISOString(),
        },
      },
    });

    // Return masked key for display
    const masked = apiKey.slice(0, 7) + '••••••••' + apiKey.slice(-4);

    res.json({
      success: true,
      message: 'Groq API key verified and saved.',
      maskedKey: masked,
    });
  } catch (error) {
    console.error('[settings/groq] Error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── GET /api/settings/groq ──────────────────────────────────────────────────
// Return Groq key status (never expose the raw key).

router.get('/groq', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const settings = (tenant?.settings as Record<string, any>) || {};

    let maskedKey: string | null = null;
    if (settings.groqApiKey) {
      try {
        const plain = decryptCredential(settings.groqApiKey);
        maskedKey = plain.slice(0, 7) + '••••••••' + plain.slice(-4);
      } catch {
        maskedKey = null;
      }
    }

    res.json({
      configured: !!maskedKey,
      maskedKey,
      verified: !!settings.groqKeyVerified,
      updatedAt: settings.groqKeyUpdatedAt || null,
      usingPlatformKey: !maskedKey, // true when tenant hasn't set their own key
    });
  } catch (error) {
    console.error('[settings/groq GET] Error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─── DELETE /api/settings/groq ───────────────────────────────────────────────
// Remove the tenant's Groq API key (reverts to platform default).

router.delete('/groq', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenant = await prisma.tenant.findUnique({ where: { id: req.tenantId } });
    const existingSettings = (tenant?.settings as Record<string, any>) || {};

    const { groqApiKey, groqKeyVerified, groqKeyUpdatedAt, ...rest } = existingSettings;

    await prisma.tenant.update({
      where: { id: req.tenantId },
      data: { settings: rest },
    });

    res.json({ success: true, message: 'Groq API key removed. Using platform default.' });
  } catch (error) {
    console.error('[settings/groq DELETE] Error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
