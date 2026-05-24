import { NextResponse } from 'next/server'
import { ACCESS_TOKEN_COOKIE, USER_COOKIE } from '@/lib/auth'

export async function POST() {
  const response = NextResponse.json({ ok: true })

  response.cookies.set(ACCESS_TOKEN_COOKIE, '', {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 0,
  })

  response.cookies.set(USER_COOKIE, '', {
    httpOnly: false,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 0,
  })

  return response
}
