import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { prisma } from '@/lib/prisma'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * Resolve the current user from the vf_browser_id cookie.
 * Returns userId, tenantId, email if the user exists, otherwise null.
 */
async function resolveAuth(): Promise<{ userId: string; tenantId: string; email: string } | null> {
  try {
    const cookieStore = await cookies()
    const browserId = cookieStore.get('vf_browser_id')?.value
    if (!browserId) return null
    const email = `user-${browserId.slice(0, 8)}@voiceflow.local`
    const user = await prisma.user.findUnique({ where: { email } })
    if (!user) return null
    return { userId: user.id, tenantId: user.tenantId, email: user.email }
  } catch {
    return null
  }
}

/**
 * Generic proxy: authenticates via cookie then forwards to the Express backend.
 * Passes userId/tenantId as trusted headers so Express doesn't need JWT.
 */
async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params

  const auth = await resolveAuth()
  if (!auth) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  }

  // Reconstruct the backend URL
  const backendPath = path.join('/')
  const url = new URL(`/${backendPath}`, BACKEND_URL)

  // Forward query parameters
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value)
  })

  // Build headers — add auth context, forward content-type
  const headers: Record<string, string> = {
    'x-user-id': auth.userId,
    'x-tenant-id': auth.tenantId,
    'x-user-email': auth.email,
  }

  const contentType = req.headers.get('content-type')
  if (contentType) {
    headers['content-type'] = contentType
  }

  // Forward body for non-GET/HEAD requests
  let body: ArrayBuffer | undefined
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    body = await req.arrayBuffer()
  }

  try {
    const resp = await fetch(url.toString(), {
      method: req.method,
      headers,
      body: body ? Buffer.from(body) : undefined,
    })

    const respBody = await resp.arrayBuffer()

    return new NextResponse(respBody, {
      status: resp.status,
      headers: {
        'content-type': resp.headers.get('content-type') || 'application/json',
      },
    })
  } catch (error) {
    console.error('Backend proxy error:', error)
    return NextResponse.json({ error: 'Backend unavailable' }, { status: 502 })
  }
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const DELETE = proxy
export const PATCH = proxy
