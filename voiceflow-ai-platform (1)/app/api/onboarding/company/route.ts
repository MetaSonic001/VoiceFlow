import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'

export async function POST(req: Request) {
  const session = await auth()
  const userId = session.userId
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  const body = await req.json().catch(() => ({}))
  const { name } = body
  if (!name) return NextResponse.json({ error: 'Missing name' }, { status: 400 })

  // Resolve user email
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
