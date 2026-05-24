import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'
import { buildAuthHeaders, getBackendUrl, getSessionFromCookies } from '@/lib/auth'

async function proxyRequest(request: NextRequest, pathSegments: string[]) {
  const cookieStore = await cookies()
  const session = getSessionFromCookies(cookieStore)

  if (!session) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 })
  }

  const backendPath = `/${pathSegments.join('/')}`
  const url = new URL(request.url)
  const targetUrl = `${getBackendUrl()}${backendPath}${url.search}`

  const headers = new Headers()
  const authHeaders = buildAuthHeaders(session)
  Object.entries(authHeaders).forEach(([key, value]) => {
    headers.set(key, value)
  })

  const contentType = request.headers.get('content-type')
  if (contentType) {
    headers.set('content-type', contentType)
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: 'no-store',
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.arrayBuffer()
  }

  const backendResponse = await fetch(targetUrl, init)
  const responseBody = await backendResponse.arrayBuffer()

  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      'content-type': backendResponse.headers.get('content-type') || 'application/json',
    },
  })
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxyRequest(request, path)
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxyRequest(request, path)
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxyRequest(request, path)
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxyRequest(request, path)
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  return proxyRequest(request, path)
}
