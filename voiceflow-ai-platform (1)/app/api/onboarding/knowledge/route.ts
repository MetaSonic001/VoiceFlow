import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'

export async function POST(req: Request) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'

  try {
    const forwardRes = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/knowledge`, {
      method: 'POST',
      headers: {
        'Content-Type': req.headers.get('content-type') || 'multipart/form-data',
        'x-tenant-id': DEMO_TENANT,
        'x-user-id': DEMO_USER,
      },
      body: req.body,
      // @ts-ignore
      duplex: 'half',
    })

    const text = await forwardRes.text()
    return new NextResponse(text, { status: forwardRes.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
