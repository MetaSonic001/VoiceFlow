import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_TENANT = 'demo-tenant'
const DEMO_USER = 'demo-user'
const DEMO_EMAIL = 'demo@voiceflow.local'

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}))
  const { name, role, templateId, description, channels, brandId } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })

  try {
    const tenantId = DEMO_TENANT

    const agent = await prisma.agent.create({
      data: {
        name,
        tenantId,
        userId: DEMO_USER,
        ...(description ? { description } : {}),
        ...(channels ? { channels } : {}),
        ...(templateId ? { templateId } : {}),
        ...(brandId ? { brandId } : {}),
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

    // No mirror to backend — Prisma writes to the same DB that the Python backend reads
    return NextResponse.json({ success: true, agent_id: agent.id })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
