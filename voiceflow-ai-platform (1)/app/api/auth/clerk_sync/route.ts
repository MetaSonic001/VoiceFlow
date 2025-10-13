import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { prisma } from '@/lib/prisma'

export async function POST(req: NextRequest) {
  // Server-side endpoint: verify Clerk auth and forward a trusted request to the Python backend
  const session = await auth()
  const userId = session.userId
  const getToken = (session as any).getToken
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  // Try to resolve email from the Clerk session first (auth() may include user info)
  // @ts-ignore
  let email = (session.user as any)?.primary_email_address || (session.user as any)?.email || null

  // Attempt to get a token and extract claims if email still unresolved, but don't let getToken errors bubble up
  try {
    if (!email && typeof getToken === 'function') {
      try {
        const token = await getToken({ template: 'session' })
        if (token) {
          try {
            let claims: any = null
            if (typeof token === 'string') {
              const parts = token.split('.')
              if (parts.length >= 2) {
                const payload = parts[1]
                const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
                const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
                const json = Buffer.from(padded, 'base64').toString('utf8')
                claims = JSON.parse(json)
              }
            } else if (typeof token === 'object') {
              // @ts-ignore
              claims = token.claims || token
            }
            if (claims) {
              email = claims.email || claims['email'] || null
            }
          } catch (e) {
            // non-fatal: couldn't decode token claims
            console.warn('Failed to decode clerk token claims', e)
          }
        }
      } catch (clerkErr) {
        // Don't fail hard if Clerk getToken returns an error (some Clerk setups don't expose the template)
        console.warn('Clerk getToken() failed; falling back to other resolution methods', clerkErr)
      }
    }

    // If still unresolved, try Clerk REST API when API key is available
    const clerkApiKey = process.env.CLERK_API_KEY
    if (!email && clerkApiKey) {
      const r = await fetch(`https://api.clerk.com/v1/users/${userId}`, { headers: { Authorization: `Bearer ${clerkApiKey}` } })
      if (r.ok) {
        const data = await r.json()
        email = data.email_addresses?.[0]?.email_address || data.primary_email_address || data.email || null
      }
    }

    if (!email) return NextResponse.json({ error: 'Unable to resolve user email from Clerk' }, { status: 400 })

    // Forward to Python backend's /auth/clerk_sync using BACKEND_INTERNAL_KEY for server-to-server auth
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const backendKey = process.env.BACKEND_API_KEY || ''
    console.log(`clerk_sync: resolved email=${email}; forwarding to backend ${backendUrl}/auth/clerk_sync`)
    const resp = await fetch(`${backendUrl.replace(/\/$/, '')}/auth/clerk_sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': backendKey,
      },
      body: JSON.stringify({ email }),
    })

    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      console.error('Backend returned non-OK for /auth/clerk_sync', { status: resp.status, body })
      return NextResponse.json({ error: 'Backend error', details: body }, { status: resp.status })
    }

    // Determine onboarding status locally and include it in the response so the client can redirect immediately
    try {
      const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail: email } })
      const needs_onboarding = !progress

      // Attach the flag to the backend response payload and return
      const combined = Object.assign({}, body, { needs_onboarding })
      return NextResponse.json(combined)
    } catch (e) {
      // If Prisma check fails, still return backend response but note the error
      const combined = Object.assign({}, body, { needs_onboarding: null, onboarding_error: String(e) })
      return NextResponse.json(combined)
    }
  } catch (err) {
    // Log the error server-side to aid debugging (visible in Next dev server logs)
    console.error('Error in /api/auth/clerk_sync:', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
