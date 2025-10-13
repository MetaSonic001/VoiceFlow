import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
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

  // Resolve the user's email from Clerk session claims when possible
  // @ts-ignore
  let userEmail = session.user?.primary_email_address || session.user?.email || null
  if (!userEmail && process.env.CLERK_API_KEY) {
    const r = await fetch(`https://api.clerk.com/v1/users/${userId}`, { headers: { Authorization: `Bearer ${process.env.CLERK_API_KEY}` } })
    if (r.ok) {
      const data = await r.json()
      userEmail = data.email_addresses?.[0]?.email_address || data.primary_email_address || null
    }
  }
  if (!userEmail) return NextResponse.json({ error: 'Unable to resolve user email' }, { status: 400 })

  try {
    const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail } })
    const tenantId = progress?.tenantId

    // Enforce tenant membership: if the user isn't associated with a tenant, return empty list
    if (!tenantId) return NextResponse.json({ agents: [], total: 0, page, limit })

    // Build filters
    const where: any = { tenantId }
    if (search) {
      where.OR = [{ name: { contains: search, mode: 'insensitive' } }]
    }
    if (status) {
      where.status = status
    }

    const total = await prisma.agent.count({ where })
    const agents = await prisma.agent.findMany({ where, orderBy: { createdAt: 'desc' }, skip: (page - 1) * limit, take: limit })

    // Attempt to enrich agents by querying the Python backend /agents endpoint (which includes stats). This is optional and best-effort.
    let backendAgentMap: Record<string, any> = {}
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      const r = await fetch(`${backendUrl.replace(/\/$/, '')}/agents`, { headers: { 'X-API-Key': backendKey } })
      if (r.ok) {
        const jb = await r.json()
        const list = jb.agents || []
        for (const a of list) backendAgentMap[a.id] = a
      }
    } catch (e) {
      // ignore enrichment failures
      console.warn('agent enrichment failed', e)
    }

    const formatted = agents.map((a: any) => {
      const backend = backendAgentMap[a.id] || {}
      return {
        id: a.id,
        name: a.name,
        tenantId: a.tenantId,
        status: backend.status || a.status || 'active',
        description: backend.description || a.description || null,
        channels: backend.channels || a.channels || [],
        phoneNumber: backend.phoneNumber || null,
        totalCalls: backend.totalCalls || 0,
        totalChats: backend.totalChats || 0,
        successRate: backend.successRate || 0,
        avgResponseTime: backend.avgResponseTime || '0s',
        lastActive: backend.lastActive || null,
        createdAt: a.createdAt,
      }
    })

    return NextResponse.json({ agents: formatted, total, page, limit })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
