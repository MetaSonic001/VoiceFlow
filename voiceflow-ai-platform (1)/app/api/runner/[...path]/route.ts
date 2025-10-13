import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export const runtime = 'nodejs'

export async function handler(req: Request, { params }: { params: { path: string[] } }) {
  const session: any = auth()
  if (!session?.userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
  const path = params.path.join('/')
  const url = `${backendUrl.replace(/\/$/, '')}/runner/${path}`

  const headers: Record<string, string> = {}
  req.headers.forEach((v, k) => {
    headers[k] = v
  })
  // add api-key for server-to-server
  if (process.env.BACKEND_API_KEY) headers['X-API-Key'] = process.env.BACKEND_API_KEY

  const res = await fetch(url, { method: req.method, headers, body: req.body })
  const text = await res.text()
  return new NextResponse(text, { status: res.status })
}

export async function GET(req: Request, ctx: any) { return handler(req, ctx) }
export async function POST(req: Request, ctx: any) { return handler(req, ctx) }
export async function PUT(req: Request, ctx: any) { return handler(req, ctx) }
export async function DELETE(req: Request, ctx: any) { return handler(req, ctx) }