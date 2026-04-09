import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { prisma } from '@/lib/prisma'

const DEMO_EMAIL = 'demo@voiceflow.local'
const DEMO_TENANT = 'demo-tenant'

export async function POST(req: NextRequest) {
  try {
    // In demo mode, ensure demo user + tenant exist and return them
    let user = await prisma.user.findUnique({
      where: { email: DEMO_EMAIL },
      include: { tenant: true, brand: true },
    })

    let needs_onboarding = !user

    if (!user) {
      let tenant = await prisma.tenant.findUnique({ where: { id: DEMO_TENANT } })
      if (!tenant) {
        tenant = await prisma.tenant.create({
          data: { id: DEMO_TENANT, name: 'Demo Organization' },
        })
      }

      let brand: any = null
      try {
        brand = await prisma.brand.create({
          data: { tenantId: tenant.id, name: 'Default Brand' },
        })
      } catch { /* brand model may not exist */ }

      user = await prisma.user.create({
        data: {
          id: 'demo-user',
          email: DEMO_EMAIL,
          tenantId: tenant.id,
          ...(brand ? { brandId: brand.id } : {}),
        },
        include: { tenant: true, brand: true },
      })
    }

    return NextResponse.json({
      needs_onboarding,
      user: {
        id: user.id,
        email: user.email,
        tenantId: user.tenantId,
        brandId: (user as any).brandId ?? null,
        tenant: user.tenant,
        brand: (user as any).brand ?? null,
      },
    })
  } catch (err) {
    console.error('Error in /api/auth/clerk_sync:', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
