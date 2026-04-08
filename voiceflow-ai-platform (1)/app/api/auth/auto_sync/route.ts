import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { cookies } from 'next/headers'
import { v4 as uuidv4 } from 'uuid'

/**
 * Auto-sync endpoint — replaces clerk_sync.
 * Finds or creates a user based on a stable browser ID stored in a cookie.
 * Returns a JWT from the Express backend for subsequent API calls.
 */
export async function POST() {
  try {
    const cookieStore = await cookies()
    let browserId = cookieStore.get('vf_browser_id')?.value

    // Generate a stable browser ID if none exists
    if (!browserId) {
      browserId = uuidv4()
    }

    const email = `user-${browserId.slice(0, 8)}@voiceflow.local`

    // Forward to Express backend's /auth/clerk_sync (handles user+tenant creation)
    const backendUrl = process.env.BACKEND_URL || process.env.NEW_BACKEND_URL || 'http://localhost:8000'
    const resp = await fetch(`${backendUrl.replace(/\/$/, '')}/auth/clerk_sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })

    const body = await resp.json().catch(() => null)
    if (!resp.ok) {
      console.error('Backend auto_sync error', { status: resp.status, body })
      return NextResponse.json({ error: 'Backend error', details: body }, { status: resp.status })
    }

    // Determine onboarding status
    let needs_onboarding = true
    try {
      const user = await prisma.user.findUnique({
        where: { email },
        include: { tenant: true },
      })
      if (user) {
        const agentCount = await prisma.agent.count({ where: { tenantId: user.tenantId } })
        needs_onboarding = agentCount === 0
      }
    } catch {
      // prisma lookup failed — assume onboarding needed
    }

    const response = NextResponse.json({
      ...body,
      needs_onboarding,
    })

    // Set stable browser ID cookie (1 year)
    response.cookies.set('vf_browser_id', browserId, {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: 365 * 24 * 60 * 60,
      path: '/',
    })

    return response
  } catch (error) {
    console.error('Error in auto_sync:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
