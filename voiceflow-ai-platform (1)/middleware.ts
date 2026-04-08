import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const isApiRoute = (req: NextRequest) => req.nextUrl.pathname.startsWith('/api/');
const isAuthRoute = (req: NextRequest) => req.nextUrl.pathname.startsWith('/api/auth/');

export default function middleware(req: NextRequest) {
  // Handle tenant isolation for API routes (exempt auth routes — tenant doesn't exist yet during sync)
  if (isApiRoute(req) && !isAuthRoute(req)) {
    const tenantId = req.headers.get('x-tenant-id');

    if (!tenantId) {
      return NextResponse.json(
        { error: 'Missing tenant ID. Please provide x-tenant-id header.' },
        { status: 400 }
      );
    }

    // Add tenant context to request headers for downstream processing
    req.headers.set('x-tenant-context', tenantId);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};