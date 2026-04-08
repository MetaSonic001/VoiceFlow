import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'
import { resolveUserEmail } from '@/lib/clerk-helpers'

export async function POST(req: Request) {
  const { userId, getToken } = await auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const body = await req.json().catch(() => ({}))
  const { name, role, templateId, description, channels } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })
  const userEmail = await resolveUserEmail()
  if (!userEmail) return NextResponse.json({ error: 'Unable to resolve user email' }, { status: 400 })

  try {
    const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail } })
    const tenantId = progress?.tenantId
    if (!tenantId) return NextResponse.json({ error: 'No tenant associated with user' }, { status: 400 })

    const agent = await prisma.agent.create({
      data: {
        name,
        tenantId,
        ...(description ? { description } : {}),
        ...(channels ? { channels } : {}),
        ...(templateId ? { templateId } : {}),
      },
    })
    // update onboarding progress with agent id
    await prisma.onboardingProgress.update({ where: { userEmail }, data: { agentId: agent.id } })

    // Create AgentConfiguration so the full profile is persisted
    try {
      await prisma.agentConfiguration.create({
        data: {
          agentId: agent.id,
          ...(templateId ? { templateId } : {}),
          agentName: name,
          ...(role ? { agentRole: role } : {}),
          ...(description ? { agentDescription: description } : {}),
          ...(channels ? { communicationChannels: channels } : {}),
        },
      })
    } catch (cfgErr) {
      console.warn('Failed to create AgentConfiguration:', cfgErr)
    }

    // Mirror creation to Express backend
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      const backendKey = process.env.BACKEND_API_KEY || ''
      const token = await getToken()
      await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': backendKey,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'x-tenant-id': tenantId,
          'x-user-id': userId,
        },
        body: JSON.stringify({ name, role, templateId, description, channels }),
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
