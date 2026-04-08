import { cookies } from 'next/headers'
import { prisma } from '@/lib/prisma'

/**
 * Resolve the current user's email address from the browser ID cookie.
 * The auto_sync flow sets a vf_browser_id cookie which maps to a stable email.
 */
export async function resolveUserEmail(): Promise<string | null> {
  try {
    const cookieStore = await cookies()
    const browserId = cookieStore.get('vf_browser_id')?.value
    if (!browserId) return null
    const email = `user-${browserId.slice(0, 8)}@voiceflow.local`
    // Verify user exists
    const user = await prisma.user.findUnique({ where: { email } })
    return user?.email || null
  } catch {
    return null
  }
}
