import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { resolveUserEmail } from '@/lib/clerk-helpers'

export async function GET() {
  const userEmail = await resolveUserEmail()
  if (!userEmail) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  try {
    const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail } })
    if (!progress) return NextResponse.json({ exists: false })
    return NextResponse.json({ exists: true, progress })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
export async function POST(req: Request) {
  const userEmail = await resolveUserEmail()
  if (!userEmail) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  const body = await req.json().catch(() => ({}))

  try {
    const up = await prisma.onboardingProgress.upsert({
      where: { userEmail },
      update: { agentId: body.agent_id || undefined, currentStep: body.current_step ?? undefined, data: body.data ?? undefined },
      create: { userEmail, agentId: body.agent_id || undefined, currentStep: body.current_step ?? undefined, data: body.data ?? undefined },
    })
    return NextResponse.json({ success: true, progress_id: up.id, agent_id: up.agentId, current_step: up.currentStep, data: up.data })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function DELETE(req: Request) {
  const userEmail = await resolveUserEmail()
  if (!userEmail) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  try {
    await prisma.onboardingProgress.deleteMany({ where: { userEmail } })
    return NextResponse.json({ deleted: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
