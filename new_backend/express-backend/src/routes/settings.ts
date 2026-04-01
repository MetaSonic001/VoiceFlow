import { Router, Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
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

export default router;
