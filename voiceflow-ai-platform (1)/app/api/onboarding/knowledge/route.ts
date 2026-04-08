import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export const runtime = 'nodejs'

export async function POST(req: Request) {
  const { userId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  const backendKey = process.env.BACKEND_API_KEY || ''
  const token = await getToken()

  // Forward the multipart request body to the Express backend
  try {
    const forwardRes = await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/knowledge`, {
      method: 'POST',
      headers: {
        // forward content-type for multipart boundary
        'Content-Type': req.headers.get('content-type') || 'multipart/form-data',
        'X-API-Key': backendKey,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'x-user-id': userId,
      },
      body: req.body,
      // @ts-ignore - needed for streaming body in Node.js fetch
      duplex: 'half',
    })

    const text = await forwardRes.text()
    return new NextResponse(text, { status: forwardRes.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
