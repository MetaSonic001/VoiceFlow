'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { ChevronRight, Home, LogOut, Settings } from 'lucide-react'
import { useAuth } from '@/providers/auth-provider'

export function DashboardHeader() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, signOut } = useAuth()

  const getBreadcrumb = () => {
    const parts = pathname.split('/').filter(Boolean)
    const breadcrumbs = [{ label: 'Dashboard', href: '/dashboard' }]

    if (parts.length > 1) {
      const label = parts[parts.length - 1]
        .split('-')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
      breadcrumbs.push({ label, href: pathname })
    }

    return breadcrumbs
  }

  const breadcrumbs = getBreadcrumb()

  return (
    <header className="sticky top-0 z-40 bg-background border-b border-border">
      <div className="px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link href="/dashboard" className="p-2 hover:bg-secondary rounded-lg transition-colors">
            <Home size={20} className="text-foreground" />
          </Link>
          {breadcrumbs.length > 1 && (
            <>
              <ChevronRight size={16} className="text-muted-foreground" />
              <nav className="flex items-center gap-1" aria-label="Breadcrumb">
                {breadcrumbs.slice(1).map((crumb) => (
                  <div key={crumb.href} className="flex items-center gap-1">
                    <Link
                      href={crumb.href}
                      className="text-sm font-serif font-semibold text-foreground hover:text-accent transition-colors"
                    >
                      {crumb.label}
                    </Link>
                  </div>
                ))}
              </nav>
            </>
          )}
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <span className="hidden md:inline text-sm font-mono text-muted-foreground">
              {user.email}
            </span>
          )}
          <Button variant="outline" size="sm" className="gap-2" asChild>
            <Link href="/dashboard/settings">
              <Settings size={16} />
              <span className="hidden sm:inline">Settings</span>
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={async () => {
              await signOut()
              router.refresh()
            }}
          >
            <LogOut size={16} />
            <span className="hidden sm:inline">Sign Out</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
