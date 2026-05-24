'use client'

import { Button } from '@/components/ui/button'
import { Plus, Edit2, Trash2, Copy } from 'lucide-react'
import { useState } from 'react'

interface Webhook {
  id: string
  event: string
  url: string
  status: 'active' | 'inactive' | 'failed'
  lastTriggered: string
  deliveryRate: number
}

const mockWebhooks: Webhook[] = [
  {
    id: '1',
    event: 'call.completed',
    url: 'https://api.example.com/webhooks/calls',
    status: 'active',
    lastTriggered: '2024-01-20 14:32',
    deliveryRate: 99.8,
  },
  {
    id: '2',
    event: 'campaign.started',
    url: 'https://api.example.com/webhooks/campaigns',
    status: 'active',
    lastTriggered: '2024-01-20 10:15',
    deliveryRate: 100,
  },
  {
    id: '3',
    event: 'agent.error',
    url: 'https://api.example.com/webhooks/errors',
    status: 'failed',
    lastTriggered: '2024-01-19 23:45',
    deliveryRate: 85.3,
  },
]

const statusColors = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-800',
  failed: 'bg-red-100 text-red-800',
}

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState(mockWebhooks)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Webhooks
          </h1>
          <p className="text-muted-foreground font-mono">
            {webhooks.length} webhooks configured
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Create Webhook
        </Button>
      </div>

      {/* Events Reference */}
      <div className="bg-card border border-border rounded-lg p-6 mb-8">
        <h2 className="text-lg font-serif font-bold text-foreground mb-4">
          Available Events
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            'call.started',
            'call.completed',
            'call.failed',
            'campaign.started',
            'campaign.completed',
            'campaign.paused',
            'agent.updated',
            'agent.error',
            'transcript.received',
            'voice.cloned',
          ].map((event) => (
            <div key={event} className="bg-background rounded p-3">
              <code className="text-sm font-mono text-accent">{event}</code>
            </div>
          ))}
        </div>
      </div>

      {/* Webhooks List */}
      <div className="space-y-4">
        {webhooks.map((webhook) => (
          <div key={webhook.id} className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <code className="text-lg font-mono font-bold text-accent">{webhook.event}</code>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[webhook.status]}`}>
                    {webhook.status.charAt(0).toUpperCase() + webhook.status.slice(1)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <p className="text-sm text-muted-foreground font-mono break-all">
                    {webhook.url}
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigator.clipboard.writeText(webhook.url)}
                  >
                    <Copy size={14} />
                  </Button>
                </div>
              </div>

              <div className="flex gap-2 ml-4">
                <Button variant="outline" size="sm">
                  <Edit2 size={16} />
                </Button>
                <Button variant="outline" size="sm" className="hover:border-red-500 hover:text-red-600">
                  <Trash2 size={16} />
                </Button>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground font-mono text-xs uppercase mb-1">Last Triggered</p>
                <p className="font-mono text-foreground">{webhook.lastTriggered}</p>
              </div>
              <div>
                <p className="text-muted-foreground font-mono text-xs uppercase mb-1">Delivery Rate</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-border rounded-full h-2">
                    <div
                      className="bg-accent h-2 rounded-full transition-all"
                      style={{ width: `${webhook.deliveryRate}%` }}
                    />
                  </div>
                  <span className="font-mono font-semibold text-foreground">{webhook.deliveryRate}%</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
