import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'

export async function POST(req: Request, { params }: { params: { id: string } }) {
  const { id } = params
  try {
    await prisma.agent.update({ where: { id }, data: { status: 'paused' } })
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}/pause`, {
        method: 'POST',
        headers: { 'x-tenant-id': DEMO_TENANT, 'x-user-id': DEMO_USER },
      })
    } catch (e) {}
    return NextResponse.json({ success: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
