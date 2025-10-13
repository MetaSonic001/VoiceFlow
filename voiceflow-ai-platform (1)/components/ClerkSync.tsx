"use client"

import { useEffect } from 'react'
import { useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'

export default function ClerkSync() {
  const { isSignedIn, user, getToken } = useUser() as any
  const router = useRouter()

  useEffect(() => {
    if (!isSignedIn) return
    ;(async () => {
      try {
        // Try to get Clerk user's primary email
        const emails = user?.emailAddresses
        const primary = emails?.find((e: any) => e?.primary)
        const email = primary?.emailAddress || user?.emailAddresses?.[0]?.emailAddress || user?.primaryEmailAddress?.emailAddress || user?.email
        if (!email) return

        // Exchange with our Next.js server route which verifies Clerk and forwards to backend
        const r = await fetch('/api/auth/clerk_sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}), // body not required; server uses auth() to inspect session
        })
        if (r.ok) {
          const res = await r.json()
          if (res?.access_token) {
            localStorage.setItem('auth_token', res.access_token)
            localStorage.setItem('auth_user', JSON.stringify(res.user))

            // Server now returns `needs_onboarding` when possible.
            // If true -> redirect to onboarding. If false -> redirect to dashboard. If null/undefined -> do nothing.
            if (res.needs_onboarding === true) {
              router.push('/onboarding')
            } else if (res.needs_onboarding === false) {
              router.push('/dashboard')
            }
          }
        } else {
          console.warn('Server clerk_sync failed', await r.text())
        }
      } catch (err) {
        console.warn('Clerk sync failed', err)
      }
    })()
  }, [isSignedIn, user])

  return null
}
