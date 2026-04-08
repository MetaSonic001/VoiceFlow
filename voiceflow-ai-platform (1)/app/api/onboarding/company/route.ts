import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { resolveUserEmail } from '@/lib/clerk-helpers'

export async function POST(req: Request) {
  const userEmail = await resolveUserEmail()
  if (!userEmail) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const body = await req.json().catch(() => ({}))
  const { name } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })

  try {
    const tenant = await prisma.tenant.create({ data: { name } })
    // ensure onboarding progress points to this tenant
    await prisma.onboardingProgress.upsert({
      where: { userEmail },
      create: { userEmail, tenantId: tenant.id },
      update: { tenantId: tenant.id },
    })
    return NextResponse.json({ success: true, tenant_id: tenant.id })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
