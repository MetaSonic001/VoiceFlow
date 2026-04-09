import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'

    const resp = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/agent-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-id': DEMO_TENANT,
        'x-user-id': DEMO_USER,
      },
      body: JSON.stringify(body),
    })

    const data = await resp.json().catch(() => null)
    if (!resp.ok) {
      return NextResponse.json({ error: 'Backend error', details: data }, { status: resp.status })
    }
    return NextResponse.json(data)
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}