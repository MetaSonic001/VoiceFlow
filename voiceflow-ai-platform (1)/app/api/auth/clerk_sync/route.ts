import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: NextRequest) {
  // Server-side endpoint: verify Clerk auth and forward a trusted request to the Python backend
  const { userId, sessionId, getToken } = auth()
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
    if (!email && token?.claims) {
      // @ts-ignore
      email = token.claims.email || token.claims['email'] || null
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
