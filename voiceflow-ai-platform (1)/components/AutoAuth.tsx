"use client"

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'

/**
 * AutoAuth — ensures the user has a session.
 * On mount, calls /api/auth/auto_sync which:
 *   1. Creates/finds a user based on a stable browser cookie
 *   2. Sets the vf_browser_id httpOnly cookie (used by the API proxy for auth)
 *   3. Returns user profile info (stored in localStorage for UI display)
 *
 * No JWT or token management needed — the proxy reads the cookie server-side.
 */
export default function AutoAuth() {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    ;(async () => {
      // If we already have user info, skip (cookie is already set from a previous visit)
      const existingUser = localStorage.getItem('auth_user')
      if (existingUser) {
        try {
          JSON.parse(existingUser) // validate it's not corrupted
          return
        } catch {
          localStorage.removeItem('auth_user')
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
          if (res.user) {
            localStorage.setItem('auth_user', JSON.stringify(res.user))
          }

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
