import { NextResponse } from 'next/server'
import {
  ACCESS_TOKEN_COOKIE,
  USER_COOKIE,
  serializeUserCookie,
} from '@/lib/auth'
import { loginRequest, ApiError } from '@/lib/api-client'

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json()

    if (!email || !password) {
      return NextResponse.json({ error: 'Email and password are required' }, { status: 400 })
    }

    const data = await loginRequest(email, password)
    const response = NextResponse.json({ user: data.user })

    response.cookies.set(ACCESS_TOKEN_COOKIE, data.access_token, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: 60 * 60 * 24,
    })

    response.cookies.set(USER_COOKIE, serializeUserCookie(data.user), {
      httpOnly: false,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: 60 * 60 * 24,
    })

    return response
  } catch (error) {
    const message = error instanceof ApiError ? error.message : 'Login failed'
    const status = error instanceof ApiError ? error.status : 500
    return NextResponse.json({ error: message }, { status })
  }
}
