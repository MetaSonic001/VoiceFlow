'use client'

import { Button } from '@/components/ui/button'
import { Plus, MoreVertical, Play, Pause, Edit2, Trash2 } from 'lucide-react'
import { useState } from 'react'

interface Campaign {
  id: string
  name: string
  description: string
  status: 'active' | 'paused' | 'completed' | 'draft'
  agent: string
  totalContacts: number
  contactsReached: number
  successRate: number
  startDate: string
  endDate?: string
}

const mockCampaigns: Campaign[] = [
  {
    id: '1',
    name: 'Q4 Customer Retention',
    description: 'Reach out to inactive customers with special offers',
    status: 'active',
    agent: 'Customer Support Agent',
    totalContacts: 5000,
    contactsReached: 3400,
    successRate: 68,
    startDate: '2024-01-01',
    endDate: '2024-03-31',
  },
  {
    id: '2',
    name: 'Lead Qualification Pipeline',
    description: 'Automated qualification calls for new sales leads',
    status: 'active',
    agent: 'Sales Outreach Bot',
    totalContacts: 2000,
    contactsReached: 1850,
    successRate: 85,
    startDate: '2024-01-15',
  },
  {
    id: '3',
    name: 'Customer Feedback Survey',
    description: 'Collect NPS and satisfaction ratings',
    status: 'paused',
    agent: 'Survey Assistant',
    totalContacts: 1500,
    contactsReached: 420,
    successRate: 92,
    startDate: '2024-01-10',
  },
  {
    id: '4',
    name: 'Appointment Confirmation',
    description: 'Confirm upcoming appointments 24 hours before',
    status: 'completed',
    agent: 'Appointment Scheduler',
    totalContacts: 800,
    contactsReached: 780,
    successRate: 87,
    startDate: '2024-01-05',
    endDate: '2024-01-30',
  },
]

const statusColors = {
  active: 'bg-green-100 text-green-800',
  paused: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-blue-100 text-blue-800',
  draft: 'bg-gray-100 text-gray-800',
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState(mockCampaigns)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Campaigns
          </h1>
          <p className="text-muted-foreground font-mono">
            {campaigns.length} campaigns
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Create Campaign
        </Button>
      </div>

      {/* Campaigns List */}
      <div className="space-y-4">
        {campaigns.map((campaign) => (
          <div key={campaign.id} className="bg-card border border-border rounded-lg overflow-hidden">
            {/* Main Row */}
            <div
              onClick={() => setExpandedId(expandedId === campaign.id ? null : campaign.id)}
              className="p-6 flex items-center justify-between cursor-pointer hover:bg-background/50 transition-colors"
            >
              <div className="flex-1">
                <div className="flex items-center gap-4 mb-2">
                  <h3 className="text-lg font-serif font-bold text-foreground">
                    {campaign.name}
                  </h3>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${statusColors[campaign.status]}`}>
                    {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mb-3">
                  {campaign.description}
                </p>
                
                {/* Stats */}
                <div className="grid grid-cols-4 gap-6 text-sm">
                  <div>
                    <p className="text-muted-foreground font-mono text-xs uppercase mb-1">Agent</p>
                    <p className="font-serif font-semibold text-foreground">{campaign.agent}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground font-mono text-xs uppercase mb-1">Progress</p>
                    <p className="font-serif font-semibold text-foreground">
                      {campaign.contactsReached}/{campaign.totalContacts}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground font-mono text-xs uppercase mb-1">Success Rate</p>
                    <p className="font-serif font-semibold text-foreground">{campaign.successRate}%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground font-mono text-xs uppercase mb-1">Started</p>
                    <p className="font-serif font-semibold text-foreground">{campaign.startDate}</p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="ml-6 flex items-center gap-2">
                {campaign.status === 'active' ? (
                  <Button size="sm" variant="outline">
                    <Pause size={16} />
                  </Button>
                ) : campaign.status === 'paused' ? (
                  <Button size="sm" variant="outline">
                    <Play size={16} />
                  </Button>
                ) : null}
                <Button size="sm" variant="outline">
                  <Edit2 size={16} />
                </Button>
                <Button size="sm" variant="outline" className="hover:border-red-500 hover:text-red-600">
                  <Trash2 size={16} />
                </Button>
                <Button size="sm" variant="ghost">
                  <MoreVertical size={16} />
                </Button>
              </div>
            </div>

            {/* Expandable Details */}
            {expandedId === campaign.id && (
              <div className="border-t border-border bg-background px-6 py-4">
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <p className="text-sm text-muted-foreground font-mono uppercase mb-2">Reach Rate</p>
                    <div className="w-full bg-border rounded-full h-2 mb-2">
                      <div
                        className="bg-accent h-2 rounded-full transition-all"
                        style={{ width: `${(campaign.contactsReached / campaign.totalContacts) * 100}%` }}
                      />
                    </div>
                    <p className="text-sm font-serif font-semibold text-foreground">
                      {Math.round((campaign.contactsReached / campaign.totalContacts) * 100)}%
                    </p>
                  </div>
                  
                  <div>
                    <p className="text-sm text-muted-foreground font-mono uppercase mb-2">Success Rate</p>
                    <div className="w-full bg-border rounded-full h-2 mb-2">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all"
                        style={{ width: `${campaign.successRate}%` }}
                      />
                    </div>
                    <p className="text-sm font-serif font-semibold text-foreground">
                      {campaign.successRate}%
                    </p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground font-mono uppercase mb-2">Duration</p>
                    <p className="text-sm font-serif font-semibold text-foreground">
                      {campaign.startDate} {campaign.endDate ? `to ${campaign.endDate}` : '(Ongoing)'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
