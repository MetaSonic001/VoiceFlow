'use client'

import Link from 'next/link'
import { ArrowRight, Phone, MessageSquare, BarChart2 } from 'lucide-react'

interface AgentCardProps {
  id: string
  name: string
  description: string
  status: 'active' | 'inactive' | 'paused'
  callsToday: number
  accuracy: number
  voices?: string[]
  href?: string
}

const statusColors = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-800',
  paused: 'bg-yellow-100 text-yellow-800',
}

const statusLabels = {
  active: 'Active',
  inactive: 'Inactive',
  paused: 'Paused',
}

export function AgentCard({
  id,
  name,
  description,
  status,
  callsToday,
  accuracy,
  voices,
  href = `/dashboard/agents/${id}`,
}: AgentCardProps) {
  return (
    <Link href={href}>
      <div className="bg-card border border-border rounded-lg p-6 hover:shadow-lg transition-shadow hover:border-accent cursor-pointer h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-serif font-bold text-foreground mb-1">
              {name}
            </h3>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {description}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ml-4 ${statusColors[status]}`}>
            {statusLabels[status]}
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-4 flex-1">
          <div className="bg-background rounded p-3">
            <div className="flex items-center gap-2 mb-1">
              <Phone size={14} className="text-muted-foreground" />
              <p className="text-xs text-muted-foreground font-mono uppercase">Calls Today</p>
            </div>
            <p className="text-xl font-serif font-bold text-foreground">{callsToday}</p>
          </div>

          <div className="bg-background rounded p-3">
            <div className="flex items-center gap-2 mb-1">
              <BarChart2 size={14} className="text-muted-foreground" />
              <p className="text-xs text-muted-foreground font-mono uppercase">Accuracy</p>
            </div>
            <p className="text-xl font-serif font-bold text-foreground">{accuracy}%</p>
          </div>
        </div>

        {/* Voices */}
        {voices && voices.length > 0 && (
          <div className="mb-4">
            <p className="text-xs text-muted-foreground font-mono uppercase mb-2">Voices</p>
            <div className="flex flex-wrap gap-2">
              {voices.map((voice) => (
                <span key={voice} className="text-xs bg-secondary text-foreground px-2 py-1 rounded font-mono">
                  {voice}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end text-accent font-semibold text-sm">
          View Details
          <ArrowRight size={16} className="ml-2" />
        </div>
      </div>
    </Link>
  )
}
