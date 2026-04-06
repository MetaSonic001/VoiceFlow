import { currentUser } from '@clerk/nextjs/server'

/**
 * Resolve the current Clerk user's primary email address.
 * Uses `currentUser()` which is the standard Clerk v6 server-side API.
 * Returns null if the user is not authenticated or has no email.
 */
export async function resolveUserEmail(): Promise<string | null> {
  const user = await currentUser()
  if (!user) return null
  const primary = user.emailAddresses.find((e: any) => e.id === user.primaryEmailAddressId)
  return primary?.emailAddress || user.emailAddresses[0]?.emailAddress || null
}
