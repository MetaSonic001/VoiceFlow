import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { getSessionFromCookies } from '@/lib/auth'

export async function GET() {
  const cookieStore = await cookies()
  const session = getSessionFromCookies(cookieStore)

  if (!session) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 })
  }

  return NextResponse.json({ user: session.user })
}
