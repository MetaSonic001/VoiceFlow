import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: Request) {
  const { userId } = auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const body = await req.json().catch(() => ({}))
  const { name } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })

  // Resolve tenant from onboarding progress
  // @ts-ignore
  let userEmail = auth().user?.primary_email_address || auth().user?.email || null
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
    if (!tenantId) return NextResponse.json({ error: 'No tenant associated with user' }, { status: 400 })

    const agent = await prisma.agent.create({ data: { name, tenantId } })
    // update onboarding progress with agent id
    await prisma.onboardingProgress.update({ where: { userEmail }, data: { agentId: agent.id } })

    // Mirror creation to Python backend to keep parity (call /agents endpoint) using BACKEND_API_KEY
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      await fetch(`${backendUrl.replace(/\/$/, '')}/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': backendKey },
        body: JSON.stringify({ tenant_id: tenantId, name }),
      })
    } catch (err) {
      // ignore backend mirror failure; still return success from Prisma
      console.warn('Failed to mirror agent to backend:', err)
    }

    return NextResponse.json({ success: true, agent_id: agent.id })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
