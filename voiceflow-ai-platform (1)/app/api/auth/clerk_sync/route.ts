import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { resolveUserEmail } from '@/lib/clerk-helpers'
import { prisma } from '@/lib/prisma'

/**
 * Legacy clerk_sync kept for backward compatibility.
 * New flow uses /api/auth/auto_sync instead.
 */
export async function POST(req: NextRequest) {
  try {
    const email = await resolveUserEmail()
    if (!email) return NextResponse.json({ error: 'Unable to resolve user email' }, { status: 400 })

    // Forward to Express backend's /auth/clerk_sync
    const backendUrl = process.env.BACKEND_URL || process.env.NEW_BACKEND_URL || 'http://localhost:8000'
    const backendKey = process.env.BACKEND_API_KEY || ''
    console.log(`clerk_sync: resolved email=${email}; forwarding to backend ${backendUrl}/auth/clerk_sync`)
    const resp = await fetch(`${backendUrl.replace(/\/$/, '')}/auth/clerk_sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': backendKey,
      },
      body: JSON.stringify({ email }),
    })

    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      console.error('Backend returned non-OK for /auth/clerk_sync', { status: resp.status, body })
      return NextResponse.json({ error: 'Backend error', details: body }, { status: resp.status })
    }

    // Determine onboarding status locally
    try {
      let user = await prisma.user.findUnique({
        where: { email },
        include: { tenant: true, brand: true },
      });

      let needs_onboarding = !user;

      if (!user) {
        const tenant = await prisma.tenant.create({
          data: { name: `${email.split('@')[0]}'s Organization` },
        });

        let brand: any = null;
        try {
          brand = await prisma.brand.create({
            data: { tenantId: tenant.id, name: 'Default Brand' },
          });
        } catch { /* brand model may not exist */ }

        user = await prisma.user.create({
          data: {
            email,
            tenantId: tenant.id,
            ...(brand ? { brandId: brand.id } : {}),
          },
          include: { tenant: true, brand: true },
        });

        console.log(`Created new tenant ${tenant.id} for user ${email}`);
      }

      return NextResponse.json({
        ...body,
        needs_onboarding,
        user: {
          id: user.id,
          email: user.email,
          tenantId: user.tenantId,
          brandId: (user as any).brandId ?? null,
          tenant: user.tenant,
          brand: (user as any).brand ?? null,
        },
      });
    } catch (e) {
      const combined = Object.assign({}, body, { needs_onboarding: null, onboarding_error: String(e) })
      return NextResponse.json(combined)
    }
  } catch (err) {
    console.error('Error in /api/auth/clerk_sync:', err)
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
