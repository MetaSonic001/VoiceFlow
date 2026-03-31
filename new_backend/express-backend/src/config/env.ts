/**
 * Environment variable validation for the Express backend.
 * Called at the top of index.ts before any routes are registered.
 * Throws immediately with a clear list of missing variables.
 */
import Joi from 'joi';

const envSchema = Joi.object({
  // Database
  DATABASE_URL: Joi.string().uri().required(),

  // Redis
  REDIS_HOST: Joi.string().required(),
  REDIS_PORT: Joi.number().integer().default(6379),

  // Clerk
  CLERK_SECRET_KEY: Joi.string().required(),

  // Groq LLM
  GROQ_API_KEY: Joi.string().required(),

  // Twilio
  TWILIO_ACCOUNT_SID: Joi.string().optional(),
  TWILIO_AUTH_TOKEN: Joi.string().optional(),

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
