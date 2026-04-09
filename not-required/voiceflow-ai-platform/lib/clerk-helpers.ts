/**
 * Demo mode: returns a fixed demo email.
 * In production, this would resolve the current user's email from Clerk.
 */
export async function resolveUserEmail(): Promise<string | null> {
  return 'demo@voiceflow.local'
}
