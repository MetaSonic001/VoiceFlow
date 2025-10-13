import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: Request, { params }: { params: { id: string } }) {
  const session: any = auth()
  const userId = session?.userId
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const { id } = params
  try {
    await prisma.agent.update({ where: { id }, data: { status: 'paused' } })
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      await fetch(`${backendUrl.replace(/\/$/, '')}/agents/${id}/pause`, { method: 'POST', headers: { 'X-API-Key': backendKey } })
    } catch (e) {}
    return NextResponse.json({ success: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
