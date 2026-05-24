export type AgentStatus = 'active' | 'inactive' | 'paused' | 'draft'

export interface Agent {
  id: string
  tenantId: string
  brandId?: string | null
  userId?: string | null
  name: string
  status: AgentStatus
  description?: string | null
  voiceType?: string | null
  totalCalls?: number
  totalChats?: number
  successRate?: number | null
  avgResponseTime?: number | null
  createdAt?: string | null
  updatedAt?: string | null
}

export interface AgentsListResponse {
  agents: Agent[]
  total: number
  page: number
  limit: number
}

export interface AnalyticsOverview {
  totalInteractions?: number
  activeAgents?: number
  successRate?: number | null
  avgResponseTime?: string
}
