'use client'

import type { AuthUser } from '@/types/auth'

export async function clientFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers)

  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, {
    ...init,
    headers,
    credentials: 'include',
  })

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(typeof data.error === 'string' ? data.error : 'Request failed')
  }

  return data as T
}

export function loginClient(email: string, password: string) {
  return clientFetch<{ user: AuthUser }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function signupClient(email: string, password: string) {
  return clientFetch<{ user: AuthUser }>('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function logoutClient() {
  return clientFetch<{ ok: boolean }>('/api/auth/logout', { method: 'POST' })
}

export function getMeClient() {
  return clientFetch<{ user: AuthUser }>('/api/auth/me')
}

export function backendProxy<T>(path: string, init: RequestInit = {}) {
  const normalized = path.startsWith('/') ? path.slice(1) : path
  return clientFetch<T>(`/api/backend/${normalized}`, init)
}
