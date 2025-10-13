import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@clerk/nextjs/server'

export async function GET() {
  const { userId } = auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  try {
    // Map Clerk userId to email via Clerk API if CLERK_API_KEY provided, else rely on local token claims
    // For simplicity, attempt to read email from auth() token claims
    // @ts-ignore
    const email = auth().user?.primary_email_address || auth().user?.email || null

    // Fallback: try to read from CLERK_API_KEY via REST API (optional)
    let userEmail = email
    if (!userEmail && process.env.CLERK_API_KEY) {
      // fetch user details
      const r = await fetch(`https://api.clerk.com/v1/users/${userId}`, { headers: { Authorization: `Bearer ${process.env.CLERK_API_KEY}` } })
      if (r.ok) {
        const data = await r.json()
        userEmail = data.email_addresses?.[0]?.email_address || data.primary_email_address || null
      }
    }

    if (!userEmail) return NextResponse.json({ error: 'Unable to resolve user email' }, { status: 400 })

    const progress = await prisma.onboardingProgress.findUnique({ where: { userEmail } })
    if (!progress) return NextResponse.json({ exists: false })
    return NextResponse.json({ exists: true, progress })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}

export async function POST(req: Request) {
  const { userId } = auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })

  const body = await req.json().catch(() => ({}))
  // expected: { agent_id?, current_step?, data? }
  // Determine user's email as above
  // @ts-ignore
  let userEmail = auth().user?.primary_email_address || auth().user?.email || null
  if (!userEmail && process.env.CLERK_API_KEY) {
    const r = await fetch(`https://api.clerk.com/v1/users/${userId}`, { headers: { Authorization: `Bearer ${process.env.CLERK_API_KEY}` } })
    if (r.ok) {
      const data = await r.json()
      userEmail = data.email_addresses?.[0]?.email_address || data.primary_email_address || null
    }
  }
  if (!userEmail) return NextResponse.json({ error: 'Unable to resolve user email' }, { status: 400 })

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
  const { userId } = auth()
  if (!userId) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  // Determine email
  // @ts-ignore
  let userEmail = auth().user?.primary_email_address || auth().user?.email || null
  if (!userEmail && process.env.CLERK_API_KEY) {
    const r = await fetch(`https://api.clerk.com/v1/users/${userId}`, { headers: { Authorization: `Bearer ${process.env.CLERK_API_KEY}` } })
    if (r.ok) {
      const data = await r.json()
      userEmail = data.email_addresses?.[0]?.email_address || data.primary_email_address || null
    }
  }
  if (!userEmail) return NextResponse.json({ error: 'Unable to resolve user email' }, { status: 400 })

  try {
    await prisma.onboardingProgress.deleteMany({ where: { userEmail } })
    return NextResponse.json({ deleted: true })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 })
  }
}
