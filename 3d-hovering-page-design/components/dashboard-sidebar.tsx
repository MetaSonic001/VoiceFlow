'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight, Zap, Mic, BookOpen, Mail, BarChart3, Settings, Users, Phone, Webhook, Gauge, FileText, LogOut, Home } from 'lucide-react'

const navSections = [
  {
    label: 'Core',
    items: [
      { icon: Home, label: 'Dashboard', href: '/dashboard' },
      { icon: Zap, label: 'Voice Agent', href: '/dashboard/voice-agent' },
      { icon: BookOpen, label: 'Voice Library', href: '/dashboard/voice-library' },
      { icon: Mail, label: 'Campaigns', href: '/dashboard/campaigns' },
    ]
  },
  {
    label: 'Configuration',
    items: [
      { icon: Gauge, label: 'Agent Builder', href: '/dashboard/agents/builder' },
      { icon: Webhook, label: 'Webhooks', href: '/dashboard/webhooks' },
      { icon: Phone, label: 'Phone Numbers', href: '/dashboard/phone-numbers' },
      { icon: FileText, label: 'SIP Trunking', href: '/dashboard/sip-trunking' },
    ]
  },
  {
    label: 'Intelligence',
    items: [
      { icon: Gauge, label: 'Live Monitor', href: '/dashboard/live-monitor' },
      { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics' },
      { icon: FileText, label: 'Reports', href: '/dashboard/reports' },
    ]
  },
  {
    label: 'Admin',
    items: [
      { icon: LogOut, label: 'Audit Logs', href: '/dashboard/audit' },
      { icon: Users, label: 'Team', href: '/dashboard/team' },
      { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
      { icon: BarChart3, label: 'Billing', href: '/dashboard/billing' },
    ]
  }
]

export function DashboardSidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border min-h-screen flex flex-col p-6">
      {/* Logo */}
      <Link href="/" className="mb-8 block">
        <h1 className="text-2xl font-serif font-bold text-sidebar-foreground">VoiceFlow</h1>
        <p className="text-xs text-sidebar-primary opacity-60 font-mono">AI Voice Agent</p>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-8 overflow-y-auto">
        {navSections.map((section) => (
          <div key={section.label}>
            <h2 className="text-xs font-mono font-semibold text-sidebar-foreground uppercase tracking-widest mb-3 opacity-70">
              {section.label}
            </h2>
            <ul className="space-y-2">
              {section.items.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 px-4 py-2 rounded-md transition-colors ${
                        isActive
                          ? 'bg-sidebar-accent text-sidebar-accent-foreground font-semibold'
                          : 'text-sidebar-foreground hover:bg-secondary hover:text-sidebar-foreground'
                      }`}
                    >
                      <Icon size={18} />
                      <span className="flex-1 text-sm">{item.label}</span>
                      {isActive && <ChevronRight size={16} />}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="pt-6 border-t border-sidebar-border">
        <div className="text-xs text-sidebar-foreground opacity-60 font-mono space-y-1">
          <p>© 2024 VoiceFlow</p>
          <p>v1.0.0</p>
        </div>
      </div>
    </aside>
  )
}
