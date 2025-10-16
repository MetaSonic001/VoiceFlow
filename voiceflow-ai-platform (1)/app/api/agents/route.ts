import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'

export async function GET(req: Request) {
  const session: any = auth()
  const userId = session?.userId
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  // Query params: page, limit, search, status
  const url = new URL(req.url)
  const page = Math.max(1, Number(url.searchParams.get('page')) || 1)
  const limit = Math.min(200, Math.max(1, Number(url.searchParams.get('limit')) || 20))
  const search = url.searchParams.get('search') || ''
  const status = url.searchParams.get('status') || ''

  try {
    // Call the new backend /api/agents endpoint
    const backendUrl = process.env.NEW_BACKEND_URL || 'http://localhost:3001'
    const backendKey = process.env.BACKEND_API_KEY || ''

    const backendReqUrl = new URL(`${backendUrl.replace(/\/$/, '')}/api/agents`)
    if (page) backendReqUrl.searchParams.set('page', String(page))
    if (limit) backendReqUrl.searchParams.set('limit', String(limit))
    if (search) backendReqUrl.searchParams.set('search', search)
    if (status) backendReqUrl.searchParams.set('status', status)

    const r = await fetch(backendReqUrl.toString(), {
      headers: {
        'X-API-Key': backendKey,
        'Authorization': req.headers.get('authorization') || '',
        'x-tenant-id': 'default-tenant', // Add tenant header
        'x-user-id': userId
      }
    })

    if (r.ok) {
      const data = await r.json()
      return NextResponse.json(data)
    } else {
      console.error('New backend agents request failed:', r.status, await r.text())
      return NextResponse.json({ agents: [], total: 0, page, limit })
    }
  } catch (err) {
    console.error('Failed to fetch agents from new backend:', err)
    return NextResponse.json({ agents: [], total: 0, page, limit })
  }
}