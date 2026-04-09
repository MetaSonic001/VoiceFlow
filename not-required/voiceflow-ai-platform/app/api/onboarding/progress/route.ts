import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_EMAIL = 'demo@voiceflow.local'

export async function GET() {
  try {
    const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail: DEMO_EMAIL } })
    if (!progress) return NextResponse.json({ exists: false })
    return NextResponse.json({ exists: true, progress })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}))

  try {
    const up = await prisma.onboardingProgress.upsert({
      where: { userEmail: DEMO_EMAIL },
      update: { agentId: body.agent_id || undefined, currentStep: body.current_step ?? undefined, data: body.data ?? undefined },
      create: { userEmail: DEMO_EMAIL, agentId: body.agent_id || undefined, currentStep: body.current_step ?? undefined, data: body.data ?? undefined },
    })
    return NextResponse.json({ success: true, progress_id: up.id, agent_id: up.agentId, current_step: up.currentStep, data: up.data })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function DELETE(req: Request) {
  try {
    await prisma.onboardingProgress.deleteMany({ where: { userEmail: DEMO_EMAIL } })
    return NextResponse.json({ deleted: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
