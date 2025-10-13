import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export const runtime = 'nodejs'

export async function POST(req: Request) {
  const { userId } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  const backendKey = process.env.BACKEND_API_KEY || ''

  // Forward the multipart request body to the Python backend
  try {
    const forwardRes = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/knowledge`, {
      method: 'POST',
      headers: {
        // forward content-type and other headers
        'Content-Type': req.headers.get('content-type') || 'multipart/form-data',
        'X-API-Key': backendKey,
      },
      body: req.body,
    })

    const text = await forwardRes.text()
    return new NextResponse(text, { status: forwardRes.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
