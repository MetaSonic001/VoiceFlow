import twilio from 'twilio';
import { PrismaClient } from '@prisma/client';
import { decryptCredential } from './credentialsService';

type TwilioClient = ReturnType<typeof twilio>;

interface CachedClient {
  client: TwilioClient;
  expiresAt: number;
}

// In-memory cache: tenantId → { client, expiresAt }
const clientCache = new Map<string, CachedClient>();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Resolve a tenant's decrypted Twilio credentials from the database.
 * Returns null if the tenant has no stored credentials.
 */
export async function getTenantTwilioCreds(
  prisma: PrismaClient,
  tenantId: string,
): Promise<{ accountSid: string; authToken: string } | null> {
  const tenant = await prisma.tenant.findUnique({ where: { id: tenantId } });
  const settings = (tenant?.settings as Record<string, any>) || {};

  const encSid = settings.twilioAccountSid;
  const encToken = settings.twilioAuthToken;

  if (!encSid || !encToken) return null;

  try {
    return {
      accountSid: decryptCredential(encSid),
      authToken: decryptCredential(encToken),
    };
  } catch {
    console.error(`[twilioClient] Failed to decrypt credentials for tenant ${tenantId}`);
    return null;
  }
}

/**
 * Get (or create and cache) a Twilio REST client for a given tenant.
 * Falls back to process.env credentials if no per-tenant creds exist.
 * Throws if no credentials are available at all.
 */
export async function getTwilioClient(
  prisma: PrismaClient,
  tenantId: string,
): Promise<TwilioClient> {
  // Check cache first
  const cached = clientCache.get(tenantId);
  if (cached && cached.expiresAt > Date.now()) {
    return cached.client;
  }

  // Load tenant credentials
  const creds = await getTenantTwilioCreds(prisma, tenantId);

  let sid: string;
  let token: string;

  if (creds) {
    sid = creds.accountSid;
    token = creds.authToken;
  } else if (process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN) {
    sid = process.env.TWILIO_ACCOUNT_SID;
    token = process.env.TWILIO_AUTH_TOKEN;
  } else {
    throw new Error(
      `No Twilio credentials available for tenant ${tenantId}. ` +
      'Configure them in Settings → Integrations.',
    );
  }

  const client = twilio(sid, token);

  // Cache with TTL
  clientCache.set(tenantId, {
    client,
    expiresAt: Date.now() + CACHE_TTL_MS,
  });

  return client;
}

/**
 * Invalidate the cached Twilio client for a tenant.
 * Call this after credentials are updated.
 */
export function invalidateTwilioClientCache(tenantId: string): void {
  clientCache.delete(tenantId);
}

/**
 * Get the decrypted auth token for webhook signature validation.
 * Falls back to env var. Returns empty string if nothing available.
 */
export async function getTwilioAuthTokenForValidation(
  prisma: PrismaClient,
  tenantId: string,
): Promise<string> {
  const creds = await getTenantTwilioCreds(prisma, tenantId);
  if (creds) return creds.authToken;
  return process.env.TWILIO_AUTH_TOKEN || '';
}
