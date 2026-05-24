import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const ACCESS_TOKEN_COOKIE = 'vf_access_token'
const AUTH_ROUTES = ['/login', '/register']

export function proxy(request: NextRequest) {
  const token = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value
  const { pathname } = request.nextUrl
  const isAuthRoute = AUTH_ROUTES.includes(pathname)
  const isDashboard = pathname.startsWith('/dashboard')

  if (isDashboard && !token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/login', '/register'],
}
