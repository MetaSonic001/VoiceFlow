import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: NextRequest) {
  // Server-side endpoint: verify Clerk auth and forward a trusted request to the Python backend
  const { userId, sessionId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  // Get session user info (Clerk token used to fetch email claim)
  // Clerk provides getToken() to get clerk jwt; use it to fetch user info
  try {
    const token = await getToken({ template: 'session' })
    // If token is missing, still try to fetch user via Clerk API token (server-side)
    // But `auth()` should provide enough
    // Fallback: use Clerk REST API with CLERK_API_KEY (optional)

    // Get user info via Clerk server-side SDK: we can call Clerk REST API
    const clerkApiKey = process.env.CLERK_API_KEY
    let email = null
    if (clerkApiKey) {
      // fetch user
      const r = await fetch(`https://api.clerk.com/v1/users/${userId}`, { headers: { Authorization: `Bearer ${clerkApiKey}` } })
      if (r.ok) {
        const data = await r.json()
        email = data.email_addresses?.[0]?.email_address || data.primary_email_address || data.email || null
      }
    }

    // Some Clerk installations expose the email in token claims; try to decode JWT if available
    if (!email && token) {
      try {
        let claims: any = null

        if (typeof token === 'string') {
          // token is a JWT string; decode the payload (base64url)
          const parts = token.split('.')
          if (parts.length >= 2) {
            const payload = parts[1]
            const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
            const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
            const json = Buffer.from(padded, 'base64').toString('utf8')
            claims = JSON.parse(json)
          }
        } else if (typeof token === 'object') {
          // token might be an object that already contains claims
          // @ts-ignore
          claims = token.claims || token
        }

        if (claims) {
          email = claims.email || claims['email'] || null
        }
      } catch (e) {
        // ignore decode/parse errors and fall back to other methods
      }
    }

    if (!email) return NextResponse.json({ error: 'Unable to resolve user email from Clerk' }, { status: 400 })

    // Forward to Python backend's /auth/clerk_sync using BACKEND_INTERNAL_KEY for server-to-server auth
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const backendKey = process.env.BACKEND_API_KEY || ''
    const resp = await fetch(`${backendUrl.replace(/\/$/, '')}/auth/clerk_sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': backendKey,
      },
      body: JSON.stringify({ email }),
    })

    const body = await resp.json()
    if (!resp.ok) return NextResponse.json({ error: 'Backend error', details: body }, { status: resp.status })

    return NextResponse.json(body)
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
