/**
 * Environment variable validation for the Express backend.
 * Called at the top of index.ts before any routes are registered.
 * Throws immediately with a clear list of missing variables.
 */
import Joi from 'joi';

const envSchema = Joi.object({
  // Database
  DATABASE_URL: Joi.string().uri().required(),

  // Redis (optional — falls back to in-memory rate limiting)
  REDIS_HOST: Joi.string().optional().default('localhost'),
  REDIS_PORT: Joi.number().integer().default(6379),

  // JWT secret for token signing/verification
  JWT_SECRET: Joi.string().optional().default('dev-secret'),

  // Groq LLM (platform fallback — tenants can bring their own key via Settings)
  GROQ_API_KEY: Joi.string().optional(),

  // Twilio
  TWILIO_ACCOUNT_SID: Joi.string().optional(),
  TWILIO_AUTH_TOKEN: Joi.string().optional(),
  TWILIO_WEBHOOK_BASE_URL: Joi.string().uri().optional(), // e.g. https://abc123.ngrok.io

  // Credential encryption (64-char hex = 32-byte key for AES-256-GCM)
  CREDENTIALS_ENCRYPTION_KEY: Joi.string().hex().length(64).optional(),

  // TTS Service (Chatterbox Turbo microservice)
  TTS_SERVICE_URL: Joi.string().uri().optional(), // e.g. http://tts-service:8003

  // MinIO / S3
  MINIO_ENDPOINT: Joi.string().optional(),
  MINIO_ACCESS_KEY: Joi.string().optional(),
  MINIO_SECRET_KEY: Joi.string().optional(),

  // ChromaDB
  CHROMA_HOST: Joi.string().default('localhost'),
  CHROMA_PORT: Joi.number().integer().default(8002),

  // General
  NODE_ENV: Joi.string().valid('development', 'production', 'test').default('development'),
  PORT: Joi.number().integer().default(8000),
}).options({ allowUnknown: true }); // allow extra vars (e.g. PATH, HOME)

export function validateEnv(): void {
  const { error } = envSchema.validate(process.env, { abortEarly: false });

  if (error) {
    const missing = error.details.map((d) => `  • ${d.message}`).join('\n');
    console.error(
      `\n❌  Missing or invalid environment variables:\n${missing}\n\n` +
        `Copy .env.example to .env and fill in the required values.\n`
    );
    process.exit(1);
  }
}
