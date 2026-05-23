'use client'

import { Button } from '@/components/ui/button'

export default function BillingPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Billing & Usage
        </h1>
        <p className="text-muted-foreground font-mono">
          View your plan, usage, and billing information
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* Current Plan */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4">Current Plan</h2>
            <div className="bg-background rounded-lg p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-2xl font-serif font-bold text-foreground">Pro Plan</h3>
                  <p className="text-sm text-muted-foreground font-mono">$299/month</p>
                </div>
                <Button className="bg-accent hover:bg-accent/90">Upgrade Plan</Button>
              </div>
              <p className="text-sm text-muted-foreground">Renews on February 1, 2024</p>
            </div>
          </div>

          {/* Usage */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4">Usage This Month</h2>
            <div className="space-y-4">
              {[
                { name: 'API Calls', used: 45000, limit: 100000 },
                { name: 'Call Minutes', used: 8500, limit: 10000 },
                { name: 'Custom Voices', used: 2, limit: 5 },
              ].map((usage) => (
                <div key={usage.name}>
                  <div className="flex justify-between mb-2">
                    <span className="font-mono text-sm text-foreground">{usage.name}</span>
                    <span className="font-mono text-sm text-muted-foreground">{usage.used.toLocaleString()} / {usage.limit.toLocaleString()}</span>
                  </div>
                  <div className="w-full bg-border rounded-full h-2">
                    <div className="bg-accent h-2 rounded-full transition-all" style={{ width: `${(usage.used / usage.limit) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="font-serif font-bold text-foreground mb-4">Payment Method</h3>
            <div className="bg-background rounded-lg p-4 mb-4">
              <p className="text-sm font-mono text-foreground">•••• •••• •••• 4242</p>
              <p className="text-xs text-muted-foreground mt-2">Expires 12/25</p>
            </div>
            <Button variant="outline" className="w-full">
              Update Payment Method
            </Button>
          </div>

          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="font-serif font-bold text-foreground mb-4">Billing History</h3>
            <div className="space-y-2">
              {['Jan 1, 2024', 'Dec 1, 2023', 'Nov 1, 2023'].map((date) => (
                <div key={date} className="flex justify-between text-sm">
                  <span className="text-foreground">{date}</span>
                  <Button variant="ghost" size="sm" className="text-accent">Download</Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
