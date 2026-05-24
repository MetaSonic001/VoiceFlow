import type { AgentsListResponse, AnalyticsOverview } from '@/types/agent'
import type { AuthSession } from '@/types/auth'
import { buildAuthHeaders, getBackendUrl } from '@/lib/auth'

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(
      typeof data.error === 'string' ? data.error : 'Request failed',
      response.status,
    )
  }
  return data as T
}

export async function backendFetch<T>(
  path: string,
  init: RequestInit = {},
  session?: AuthSession | null,
): Promise<T> {
  const headers = new Headers(init.headers)

  if (session) {
    const authHeaders = buildAuthHeaders(session)
    Object.entries(authHeaders).forEach(([key, value]) => {
      headers.set(key, value)
    })
  }

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${getBackendUrl()}${path}`, {
    ...init,
    headers,
    cache: 'no-store',
  })

  return parseResponse<T>(response)
}

export async function loginRequest(email: string, password: string) {
  return backendFetch<{ access_token: string; user: AuthSession['user'] }>(
    '/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    },
  )
}

export async function signupRequest(email: string, password: string) {
  return backendFetch<{ access_token: string; user: AuthSession['user'] }>(
    '/auth/signup',
    {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    },
  )
}

export async function getAgents(session: AuthSession) {
  return backendFetch<AgentsListResponse>('/api/agents/?limit=50', {}, session)
}

export async function getAnalyticsOverview(session: AuthSession) {
  return backendFetch<AnalyticsOverview>('/analytics/overview', {}, session)
}

export { ApiError }
