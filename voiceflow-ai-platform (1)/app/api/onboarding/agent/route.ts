import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'
const DEMO_EMAIL = 'demo@voiceflow.local'

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}))
  const { name, role, templateId, description, channels } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })

  try {
    // Use demo-tenant or look up from onboarding progress
    let tenantId = DEMO_TENANT
    const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail: DEMO_EMAIL } })
    if (progress?.tenantId) tenantId = progress.tenantId

    const agent = await prisma.agent.create({
      data: {
        name,
        tenantId,
        ...(description ? { description } : {}),
        ...(channels ? { channels } : {}),
        ...(templateId ? { templateId } : {}),
      },
    })

    // Update onboarding progress with agent id
    await prisma.onboardingProgress.upsert({
      where: { userEmail: DEMO_EMAIL },
      create: { userEmail: DEMO_EMAIL, agentId: agent.id, tenantId },
      update: { agentId: agent.id },
    })

    // Create AgentConfiguration
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

    // Mirror to Express backend
    try {
      const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
      await fetch(`${backendUrl.replace(/\/$/, '')}/onboarding/agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-tenant-id': tenantId,
          'x-user-id': DEMO_USER,
        },
        body: JSON.stringify({ name, role, templateId, description, channels }),
      })
    } catch (err) {
      console.warn('Failed to mirror agent to backend:', err)
    }

    return NextResponse.json({ success: true, agent_id: agent.id })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
