import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const { id } = params
  try {
    const agent = await prisma.agent.findUnique({ where: { id } })
    if (!agent) return NextResponse.json({ error: 'Not found' }, { status: 404 })
    let backend = null
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const r = await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}`, {
        headers: { 'x-tenant-id': DEMO_TENANT, 'x-user-id': DEMO_USER },
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
  const { id } = params
  const body = await req.json().catch(() => ({}))
  try {
    const updated = await prisma.agent.update({ where: { id }, data: body })
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-tenant-id': DEMO_TENANT, 'x-user-id': DEMO_USER },
        body: JSON.stringify(body),
      })
    } catch (e) {}
    return NextResponse.json({ success: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function DELETE(req: Request, { params }: { params: { id: string } }) {
  const { id } = params
  try {
    await prisma.agent.delete({ where: { id } })
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}`, {
        method: 'DELETE',
        headers: { 'x-tenant-id': DEMO_TENANT, 'x-user-id': DEMO_USER },
      })
    } catch (e) {}
    return NextResponse.json({ success: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
