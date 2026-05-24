import type { AuthSession, AuthUser } from '@/types/auth'

export const ACCESS_TOKEN_COOKIE = 'vf_access_token'
export const USER_COOKIE = 'vf_user'

export function getBackendUrl(): string {
  return process.env.BACKEND_API_URL || 'http://localhost:8040'
}

export function parseUserCookie(value: string | undefined): AuthUser | null {
  if (!value) return null
  try {
    return JSON.parse(decodeURIComponent(value)) as AuthUser
  } catch {
    return null
  }
}

export function serializeUserCookie(user: AuthUser): string {
  return encodeURIComponent(JSON.stringify(user))
}

export function buildAuthHeaders(session: AuthSession): HeadersInit {
  return {
    Authorization: `Bearer ${session.accessToken}`,
    'x-tenant-id': session.user.tenantId,
    'x-user-id': session.user.id,
    'x-user-email': session.user.email,
  }
}

export function getSessionFromCookies(cookieStore: {
  get: (name: string) => { value: string } | undefined
}): AuthSession | null {
  const token = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value
  const user = parseUserCookie(cookieStore.get(USER_COOKIE)?.value)

  if (!token || !user) return null
  return { accessToken: token, user }
}
