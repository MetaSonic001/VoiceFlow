'use client'

import { Button } from '@/components/ui/button'
import { Copy, Eye, EyeOff, Trash2 } from 'lucide-react'
import { useState } from 'react'

interface APIKey {
  id: string
  name: string
  key: string
  maskedKey: string
  createdAt: string
  lastUsed: string
}

const mockAPIKeys: APIKey[] = [
  {
    id: '1',
    name: 'Production API Key',
    key: 'sk_live_abc123def456ghi789jkl',
    maskedKey: 'sk_live_•••••••••••••••789jkl',
    createdAt: '2023-12-01',
    lastUsed: '2024-01-20 14:32',
  },
  {
    id: '2',
    name: 'Development API Key',
    key: 'sk_test_xyz789abc123def456ghi',
    maskedKey: 'sk_test_•••••••••••••••456ghi',
    createdAt: '2023-11-15',
    lastUsed: '2024-01-19 10:15',
  },
]

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState(mockAPIKeys)
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())

  const toggleKeyVisibility = (id: string) => {
    setVisibleKeys(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Settings
        </h1>
        <p className="text-muted-foreground font-mono">
          Manage your API keys and account settings
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* API Keys Section */}
          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-serif font-bold text-foreground mb-1">
                  API Keys
                </h2>
                <p className="text-sm text-muted-foreground font-mono">
                  Manage API keys for programmatic access
                </p>
              </div>
              <Button className="bg-accent hover:bg-accent/90">
                Create API Key
              </Button>
            </div>

            <div className="space-y-4">
              {apiKeys.map((apiKey) => (
                <div key={apiKey.id} className="bg-background border border-border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-serif font-bold text-foreground">
                        {apiKey.name}
                      </h3>
                      <p className="text-xs text-muted-foreground font-mono">
                        Created {apiKey.createdAt}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" className="hover:border-red-500 hover:text-red-600">
                      <Trash2 size={16} />
                    </Button>
                  </div>

                  <div className="flex items-center gap-2 mb-2">
                    <code className="flex-1 bg-foreground/5 rounded px-3 py-2 text-sm font-mono text-foreground break-all">
                      {visibleKeys.has(apiKey.id) ? apiKey.key : apiKey.maskedKey}
                    </code>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleKeyVisibility(apiKey.id)}
                    >
                      {visibleKeys.has(apiKey.id) ? <EyeOff size={16} /> : <Eye size={16} />}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigator.clipboard.writeText(apiKey.key)}
                    >
                      <Copy size={16} />
                    </Button>
                  </div>

                  <p className="text-xs text-muted-foreground font-mono">
                    Last used: {apiKey.lastUsed}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Webhooks Section */}
          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-serif font-bold text-foreground mb-1">
                  Webhook URLs
                </h2>
                <p className="text-sm text-muted-foreground font-mono">
                  Configure webhooks for event notifications
                </p>
              </div>
              <Button className="bg-accent hover:bg-accent/90">
                Add Webhook
              </Button>
            </div>

            <div className="space-y-4">
              {[
                { event: 'call.completed', url: 'https://api.example.com/webhooks/calls' },
                { event: 'campaign.finished', url: 'https://api.example.com/webhooks/campaigns' },
              ].map((webhook) => (
                <div key={webhook.event} className="bg-background border border-border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-mono font-semibold text-foreground">{webhook.event}</p>
                      <p className="text-sm text-muted-foreground mt-1 break-all">{webhook.url}</p>
                    </div>
                    <Button variant="outline" size="sm" className="hover:border-red-500 hover:text-red-600">
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Account Info */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="font-serif font-bold text-foreground mb-4">
              Account Info
            </h3>
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-muted-foreground font-mono uppercase mb-1">Email</p>
                <p className="font-serif text-foreground">admin@example.com</p>
              </div>
              <div>
                <p className="text-muted-foreground font-mono uppercase mb-1">Plan</p>
                <p className="font-serif text-foreground">Pro</p>
              </div>
              <div>
                <p className="text-muted-foreground font-mono uppercase mb-1">Status</p>
                <p className="font-serif text-foreground flex items-center">
                  <span className="w-2 h-2 bg-green-600 rounded-full mr-2" />
                  Active
                </p>
              </div>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h3 className="font-serif font-bold text-red-900 mb-4">
              Danger Zone
            </h3>
            <Button variant="outline" className="w-full border-red-500 text-red-600 hover:bg-red-50">
              <Trash2 size={16} className="mr-2" />
              Delete Account
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
