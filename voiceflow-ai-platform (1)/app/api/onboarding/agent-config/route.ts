import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: NextRequest) {
  const session = await auth()
  const userId = session.userId
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  try {
    const body = await req.json()

    // Forward to backend
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const backendKey = process.env.BACKEND_API_KEY || ''
    const tenantId = req.headers.get('x-tenant-id')

    const resp = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/agent-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': backendKey,
        'Authorization': req.headers.get('authorization') || '',
        ...(tenantId && { 'x-tenant-id': tenantId }),
      },
      body: JSON.stringify(body),
    })

    const data = await resp.json().catch(() => null)
    if (!resp.ok) {
      console.error('Backend returned non-OK for /onboarding/agent-config', { status: resp.status, data })
      return NextResponse.json({ error: 'Backend error', details: data }, { status: resp.status })
    }

    return NextResponse.json(data)
  } catch (err) {
    console.error('Error in /api/onboarding/agent-config:', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}