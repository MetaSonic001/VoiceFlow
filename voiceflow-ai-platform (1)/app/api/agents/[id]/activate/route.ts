import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: Request, { params }: { params: { id: string } }) {
  const { userId, orgId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const { id } = params
  try {
    await prisma.agent.update({ where: { id }, data: { status: 'active' } })
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      const token = await getToken()
      await fetch(`${backendUrl.replace(/\/$/, '')}/api/agents/${id}/activate`, {
        method: 'POST',
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
