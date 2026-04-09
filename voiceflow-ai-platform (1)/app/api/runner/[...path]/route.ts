import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'

export async function handler(req: Request, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  const url = `${backendUrl.replace(/\/$/, '')}/api/runner/${path}`

  const headers: Record<string, string> = {}

  const contentType = req.headers.get('content-type')
  if (!contentType?.includes('multipart/form-data')) {
    req.headers.forEach((v, k) => { headers[k] = v })
  } else {
    req.headers.forEach((v, k) => {
      if (k.toLowerCase() !== 'content-type') headers[k] = v
    })
  }

  // Ensure demo headers
  headers['x-tenant-id'] = headers['x-tenant-id'] || DEMO_TENANT
  headers['x-user-id'] = headers['x-user-id'] || DEMO_USER

  const res = await fetch(url, {
    method: req.method,
    headers,
    body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
    // @ts-ignore
    duplex: 'half',
  })
  const text = await res.text()
  return new NextResponse(text, { status: res.status })
}

export async function GET(req: Request, ctx: any) { return handler(req, ctx) }
export async function POST(req: Request, ctx: any) { return handler(req, ctx) }
export async function PUT(req: Request, ctx: any) { return handler(req, ctx) }
export async function DELETE(req: Request, ctx: any) { return handler(req, ctx) }