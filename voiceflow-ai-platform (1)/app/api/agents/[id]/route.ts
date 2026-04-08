import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const { userId, orgId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const { id } = params
  try {
    const agent = await prisma.agent.findUnique({ where: { id } })
    if (!agent) return NextResponse.json({ error: 'Not found' }, { status: 404 })
    // Optionally enrich from backend
    let backend = null
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      const token = await getToken()
      const r = await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}`, {
        headers: {
          'X-API-Key': backendKey,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'x-tenant-id': orgId || userId || 'default-tenant',
          'x-user-id': userId,
        },
      })
      if (r.ok) backend = await r.json()
    } catch (e) {}

    const out = {
      id: agent.id,
      name: agent.name,
      tenantId: agent.tenantId,
      status: agent.status || 'active',
      description: agent.description || null,
      channels: agent.channels || [],
      phoneNumber: agent.phoneNumber || null,
      totalCalls: agent.totalCalls || 0,
      totalChats: agent.totalChats || 0,
      successRate: agent.successRate || 0,
      avgResponseTime: agent.avgResponseTime || null,
      createdAt: agent.createdAt,
      ...(backend?.agent ? backend.agent : {}),
    }

    return NextResponse.json(out)
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function PUT(req: Request, { params }: { params: { id: string } }) {
  const { userId, orgId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const { id } = params
  const body = await req.json().catch(() => ({}))
  try {
    const updated = await prisma.agent.update({ where: { id }, data: body })
    // Mirror to python backend if present
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      const token = await getToken()
      await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': backendKey,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'x-tenant-id': orgId || userId || 'default-tenant',
          'x-user-id': userId,
        },
        body: JSON.stringify(body),
      })
    } catch (e) {}
    return NextResponse.json({ success: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function DELETE(req: Request, { params }: { params: { id: string } }) {
  const { userId, orgId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const { id } = params
  try {
    await prisma.agent.delete({ where: { id } })
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      const token = await getToken()
      await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}`, {
        method: 'DELETE',
        headers: {
          'X-API-Key': backendKey,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'x-tenant-id': orgId || userId || 'default-tenant',
          'x-user-id': userId,
        },
      })
    } catch (e) {}
    return NextResponse.json({ success: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
