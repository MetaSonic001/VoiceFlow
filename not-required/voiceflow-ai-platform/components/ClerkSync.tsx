"use client"

import { useEffect } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'

export default function ClerkSync() {
  const { isSignedIn, getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()

  // Wire up apiClient to always fetch a fresh Clerk JWT on every request
  useEffect(() => {
    if (!isSignedIn) return
    apiClient.setTokenProvider(() => getToken())
  }, [isSignedIn, getToken])

  // Sync user/tenant with the backend once on sign-in
  useEffect(() => {
    if (!isSignedIn || !user) return
    ;(async () => {
      try {
        const r = await fetch('/api/auth/clerk_sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        })
        if (r.ok) {
          const res = await r.json()
          // Persist user profile data (tenantId, brandId) — NOT tokens
          if (res?.user) {
            localStorage.setItem('auth_user', JSON.stringify(res.user))
            if (res.user.tenantId) {
              apiClient.setTenantId(res.user.tenantId)
            }
          }

          if (res.needs_onboarding === true) {
            router.push('/onboarding')
          } else if (res.needs_onboarding === false) {
            router.push('/dashboard')
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
