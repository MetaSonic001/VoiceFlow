import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_EMAIL = 'demo@voiceflow.local'

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}))
  const { name } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })

  try {
    const tenant = await prisma.tenant.create({ data: { name } })
    await prisma.onboardingProgress.upsert({
      where: { userEmail: DEMO_EMAIL },
      create: { userEmail: DEMO_EMAIL, tenantId: tenant.id },
      update: { tenantId: tenant.id },
    })
    return NextResponse.json({ success: true, tenant_id: tenant.id })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
