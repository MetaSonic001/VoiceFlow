'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { ChevronRight, Home, LogOut, Settings, Menu } from 'lucide-react'

export function DashboardHeader() {
  const pathname = usePathname()

  // Get breadcrumb from pathname
  const getBreadcrumb = () => {
    const parts = pathname.split('/').filter(Boolean)
    const breadcrumbs = [{ label: 'Dashboard', href: '/dashboard' }]

    if (parts.length > 1) {
      // Convert kebab-case to Title Case
      const label = parts[parts.length - 1]
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
      breadcrumbs.push({ label, href: pathname })
    }

    return breadcrumbs
  }

  const breadcrumbs = getBreadcrumb()

  return (
    <header className="sticky top-0 z-40 bg-background border-b border-border">
      <div className="px-8 py-4 flex items-center justify-between">
        {/* Breadcrumb Navigation */}
        <div className="flex items-center gap-2">
          <Link href="/dashboard" className="p-2 hover:bg-secondary rounded-lg transition-colors">
            <Home size={20} className="text-foreground" />
          </Link>
          {breadcrumbs.length > 1 && (
            <>
              <ChevronRight size={16} className="text-muted-foreground" />
              <nav className="flex items-center gap-1" aria-label="Breadcrumb">
                {breadcrumbs.slice(1).map((crumb, index) => (
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

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" className="gap-2">
            <Settings size={16} />
            <span className="hidden sm:inline">Settings</span>
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <LogOut size={16} />
            <span className="hidden sm:inline">Sign Out</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
