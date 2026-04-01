import 'dotenv/config';
import { validateEnv } from './config/env';

// Validate required environment variables before anything else starts up
validateEnv();

import express, { Request, Response, Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { createServer, Server as HTTPServer } from 'http';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';

// Route imports
import adminRouter from './routes/admin';
import agentsRouter from './routes/agents';
import analyticsRouter from './routes/analytics';
import authRouter from './routes/auth';
import documentsRouter from './routes/documents';
import onboardingRouter from './routes/onboarding';
import ragRouter from './routes/rag';
import ingestionRouter from './routes/ingestion';
import runnerRouter from './routes/runner';
import twilioRouter from './routes/twilio';
import twilioVoiceRouter from './routes/twilioVoice';
import settingsRouter from './routes/settings';
import usersRouter from './routes/users';
import logsRouter from './routes/logs';
import templatesRouter from './routes/templates';
import ttsRouter from './routes/tts';

// Middleware imports
import { createTenantRateLimit } from './middleware/rateLimit';
import { createClerkAuth } from './middleware/clerkAuth';
import { swaggerUi, specs } from './utils/swagger';
import { errorHandler, requestLogger, healthCheckErrorHandler } from './middleware/errorHandler';
import { syncAgentWebhookUrl } from './services/twilioProvisioningService';

// Initialize Express app
const app: Application = express();
const server: HTTPServer = createServer(app);
const startTime = Date.now();

// Initialize Prisma
const prisma = new PrismaClient();

// Initialize Clerk auth
const clerkAuth = createClerkAuth(prisma);

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Make services available in routes
app.set('prisma', prisma);

// Initialize Redis
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379', 10)
});
app.set('redis', redis);

// Rate limiting
app.use(createTenantRateLimit(redis));

// Routes
app.use('/admin', clerkAuth.authenticate, adminRouter);
app.use('/analytics', clerkAuth.authenticate, analyticsRouter);
app.use('/auth', authRouter);
app.use('/onboarding', clerkAuth.authenticate, onboardingRouter);
// Twilio voice webhooks — NO Clerk auth (Twilio sends its own signature)
app.use('/twilio/voice', twilioVoiceRouter);
// Twilio admin endpoints (numbers, etc.) — Clerk-authed
app.use('/twilio', clerkAuth.authenticate, twilioRouter);
app.use('/api/agents', clerkAuth.authenticate, agentsRouter);
app.use('/api/documents', clerkAuth.authenticate, documentsRouter);
app.use('/api/rag', clerkAuth.authenticate, ragRouter);
app.use('/api/ingestion', clerkAuth.authenticate, ingestionRouter);
app.use('/api/runner', clerkAuth.authenticate, runnerRouter);
app.use('/api/settings', clerkAuth.authenticate, settingsRouter);
app.use('/api/users', clerkAuth.authenticate, usersRouter);
app.use('/api/logs', clerkAuth.authenticate, logsRouter);
app.use('/api/templates', clerkAuth.authenticate, templatesRouter);
app.use('/api/tts', clerkAuth.authenticate, ttsRouter);

// API Documentation
// app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));

// Health check
const healthHandler = (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    version: process.env.npm_package_version || '1.0.0',
    uptime: Math.floor((Date.now() - startTime) / 1000),
    timestamp: new Date().toISOString(),
  });
};
app.get('/health', healthHandler);
app.post('/health', healthHandler);

// Error handling middleware (must be last)
app.use(requestLogger);
app.use(healthCheckErrorHandler);
app.use(errorHandler);

// Start server
const PORT = process.env.PORT || 8000;

/**
 * On startup, ensure all provisioned agents' Twilio webhook URLs
 * point to the current TWILIO_WEBHOOK_BASE_URL.
 * In development, attempts to start an ngrok tunnel first.
 */
async function setupTwilioWebhooks(): Promise<void> {
  let baseUrl = process.env.TWILIO_WEBHOOK_BASE_URL;

  // In development, try to start ngrok automatically
  if (!baseUrl && process.env.NODE_ENV !== 'production') {
    try {
      const ngrok = require('@ngrok/ngrok');
      const listener = await ngrok.forward({ addr: PORT, authtoken_from_env: true });
      baseUrl = listener.url();
      process.env.TWILIO_WEBHOOK_BASE_URL = baseUrl;
      console.log(`[setup] ngrok tunnel established: ${baseUrl}`);
    } catch (err: any) {
      console.log('[setup] ngrok not available — set TWILIO_WEBHOOK_BASE_URL manually if needed');
      return;
    }
  }

  if (!baseUrl) {
    console.log('[setup] No TWILIO_WEBHOOK_BASE_URL — skipping webhook sync');
    return;
  }

  // Find all agents that have a provisioned Twilio number
  try {
    const agents = await prisma.agent.findMany({
      where: { twilioNumberSid: { not: null } },
      select: { id: true, tenantId: true, twilioNumberSid: true },
    });

    if (agents.length === 0) {
      console.log('[setup] No provisioned agents — nothing to sync');
      return;
    }

    console.log(`[setup] Syncing webhooks for ${agents.length} provisioned agent(s)…`);
    for (const agent of agents) {
      await syncAgentWebhookUrl(prisma, agent.id, agent.tenantId, agent.twilioNumberSid!);
    }
    console.log('[setup] Webhook sync complete');
  } catch (err: any) {
    console.warn('[setup] Webhook sync failed:', err?.message);
  }
}

server.listen(PORT, () => {
  console.log(`Express server running on port ${PORT}`);

  // Non-blocking: set up Twilio webhooks after server is ready
  setupTwilioWebhooks().catch((err) => {
    console.warn('[setup] Twilio webhook setup failed:', err?.message);
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  await prisma.$disconnect();
  await redis.quit();
  server.close(() => {
    console.log('Process terminated');
  });
});

process.on('SIGINT', async () => {
  console.log('SIGINT received, shutting down gracefully');
  await prisma.$disconnect();
  await redis.quit();
  server.close(() => {
    console.log('Process terminated');
  });
});