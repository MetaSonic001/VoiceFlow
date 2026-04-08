import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export const runtime = 'nodejs'

export async function handler(req: Request, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')

  // Allow unauthenticated access for voice agent audio endpoint
  const isVoiceAgentAudio = path === 'audio'

  // Check for auth token
  const authHeader = req.headers.get('authorization')
  if (!isVoiceAgentAudio && !authHeader) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  }

  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  const url = `${backendUrl.replace(/\/$/, '')}/api/runner/${path}`

  const headers: Record<string, string> = {}

  // Don't copy content-type for FormData - let fetch set it automatically
  const contentType = req.headers.get('content-type')
  if (!contentType?.includes('multipart/form-data')) {
    req.headers.forEach((v, k) => {
      headers[k] = v
    })
  } else {
    // Copy other headers but not content-type for FormData
    req.headers.forEach((v, k) => {
      if (k.toLowerCase() !== 'content-type') {
        headers[k] = v
      }
    })
  }

  // add api-key for server-to-server
  if (process.env.BACKEND_API_KEY) headers['X-API-Key'] = process.env.BACKEND_API_KEY
  // add tenant and user headers from the proxied request
  if (!headers['x-tenant-id']) {
    headers['x-tenant-id'] = 'default-tenant'
  }
  if (isVoiceAgentAudio && !headers['x-user-id']) {
    headers['x-user-id'] = 'demo-user'
  }

  const res = await fetch(url, {
    method: req.method,
    headers,
    body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined
  })
  const text = await res.text()
  return new NextResponse(text, { status: res.status })
}

export async function GET(req: Request, ctx: any) { return handler(req, ctx) }
export async function POST(req: Request, ctx: any) { return handler(req, ctx) }
export async function PUT(req: Request, ctx: any) { return handler(req, ctx) }
export async function DELETE(req: Request, ctx: any) { return handler(req, ctx) }