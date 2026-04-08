import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export default function middleware(_req: NextRequest) {
  // All auth is handled inside the proxy route (app/api/backend/[...path]/route.ts)
  // via the vf_browser_id httpOnly cookie. No header checks needed here.
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};