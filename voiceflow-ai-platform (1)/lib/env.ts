/**
 * Environment variable validation for the Next.js app.
 * Import this module early (e.g. in lib/prisma.ts or a root layout server component).
 * Throws on startup with a clear list of missing variables instead of failing silently
 * deep inside a service call.
 */
import { z } from 'zod'

const envSchema = z.object({
  // Clerk
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: z.string().min(1, 'Clerk publishable key is required'),
  CLERK_SECRET_KEY: z.string().min(1, 'Clerk secret key is required'),

  // Database
  DATABASE_URL: z.string().url('DATABASE_URL must be a valid connection string'),

  // Backend service
  NEXT_PUBLIC_API_URL: z.string().url('NEXT_PUBLIC_API_URL must be a valid URL').optional(),
  NEW_BACKEND_URL: z.string().url('NEW_BACKEND_URL must be a valid URL').optional(),
  BACKEND_API_KEY: z.string().optional(),
})

// Allow optional vars to be missing entirely (z.string().optional() still fails on empty string)
type EnvInput = z.input<typeof envSchema>

function validateEnv() {
  const result = envSchema.safeParse(process.env as unknown as EnvInput)

  if (!result.success) {
    const missing = result.error.issues.map(
      (issue) => `  • ${issue.path.join('.')}: ${issue.message}`
    )
    throw new Error(
      `\n\n❌ Missing or invalid environment variables:\n${missing.join('\n')}\n\n` +
        `Copy .env.example to .env.local and fill in the required values.\n`
    )
  }

  return result.data
}

// Run once at module load — only on the server side
let _validated = false
export function ensureEnv() {
  if (typeof window !== 'undefined') return // skip on client
  if (_validated) return
  validateEnv()
  _validated = true
}

// Call immediately so any import of this module triggers the check
ensureEnv()
