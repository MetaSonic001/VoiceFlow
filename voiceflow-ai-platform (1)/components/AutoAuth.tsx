"use client"

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { apiClient } from '@/lib/api-client'

/**
 * AutoAuth — replaces ClerkSync.
 * On mount, checks localStorage for an existing session.
 * If none exists, calls /api/auth/auto_sync to create a user+tenant,
 * stores the JWT and user profile, then sets up the apiClient.
 */
export default function AutoAuth() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    ;(async () => {
      // Check if we already have a session
      const existingToken = localStorage.getItem('auth_token')
      const existingUser = localStorage.getItem('auth_user')

      if (existingToken && existingUser) {
        try {
          const user = JSON.parse(existingUser)
          apiClient.setTokenProvider(async () => localStorage.getItem('auth_token'))
          if (user.tenantId) apiClient.setTenantId(user.tenantId)
          return
        } catch {
          // corrupted data, re-sync below
        }
      }

      // No session — auto-create one
      try {
        const r = await fetch('/api/auth/auto_sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })
        if (r.ok) {
          const res = await r.json()
          if (res.access_token) {
            localStorage.setItem('auth_token', res.access_token)
          }
          if (res.user) {
            localStorage.setItem('auth_user', JSON.stringify(res.user))
            if (res.user.tenantId) apiClient.setTenantId(res.user.tenantId)
          }
          apiClient.setTokenProvider(async () => localStorage.getItem('auth_token'))

          // Route based on onboarding status
          if (res.needs_onboarding === true && pathname === '/') {
            router.push('/onboarding')
          }
        }
      } catch (err) {
        console.warn('Auto-auth sync failed', err)
      }
    })()
  }, [])

  return null
}
