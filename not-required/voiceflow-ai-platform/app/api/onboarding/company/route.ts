import { NextResponse } from 'next/server'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'

// Pure proxy to Python backend — stores company profile in tenant settings
export async function GET() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const r = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/company`, {
      headers: { 'x-tenant-id': DEMO_TENANT, 'x-user-id': DEMO_USER },
    })
    const data = await r.json().catch(() => ({}))
    return NextResponse.json(data, { status: r.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const r = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/company`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-id': DEMO_TENANT,
        'x-user-id': DEMO_USER,
      },
      body: JSON.stringify(body),
    })
    const data = await r.json().catch(() => ({}))
    return NextResponse.json(data, { status: r.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
