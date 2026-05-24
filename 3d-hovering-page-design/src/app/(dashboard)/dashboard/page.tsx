import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { Phone, BarChart3, Clock, Users } from 'lucide-react'
import { KPICard } from '@/components/dashboard/kpi-card'
import { AgentCard } from '@/components/agents/agent-card'
import { getAgents, getAnalyticsOverview } from '@/lib/api-client'
import { getSessionFromCookies } from '@/lib/auth'
import type { Agent, AgentStatus } from '@/types/agent'

function normalizeStatus(status?: string | null): AgentStatus {
  if (status === 'active' || status === 'paused' || status === 'inactive' || status === 'draft') {
    return status
  }
  return 'inactive'
}

export default async function DashboardPage() {
  const cookieStore = await cookies()
  const session = getSessionFromCookies(cookieStore)

  if (!session) {
    redirect('/login')
  }

  let agents: Agent[] = []
  let overview = {
    totalAgents: 0,
    activeAgents: 0,
    totalCalls: 0,
    avgSuccessRate: 0,
  }

  try {
    const [agentsResponse, analyticsResponse] = await Promise.all([
      getAgents(session),
      getAnalyticsOverview(session).catch(() => null),
    ])

    agents = agentsResponse.agents ?? []
    overview = {
      totalAgents: agents.length,
      activeAgents: analyticsResponse?.activeAgents ?? agents.filter((a) => a.status === 'active').length,
      totalCalls: analyticsResponse?.totalInteractions ?? agents.reduce((sum, a) => sum + (a.totalCalls ?? 0), 0),
      avgSuccessRate: analyticsResponse?.successRate ?? (
        agents.length > 0
          ? agents.reduce((sum, a) => sum + (a.successRate ?? 0), 0) / agents.length
          : 0
      ) ?? 0,
    }
  } catch {
    agents = []
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          AI Agents Dashboard
        </h1>
        <p className="text-muted-foreground font-mono">
          Manage and monitor your voice AI agents
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          icon={Phone}
          label="Active Agents"
          value={overview.activeAgents}
          color="accent"
        />
        <KPICard
          icon={Clock}
          label="Total Calls"
          value={overview.totalCalls}
          color="success"
        />
        <KPICard
          icon={BarChart3}
          label="Avg Success Rate"
          value={(overview.avgSuccessRate ?? 0).toFixed(1)}
          unit="%"
          color="default"
        />
        <KPICard
          icon={Users}
          label="Total Agents"
          value={overview.totalAgents}
          color="default"
        />
      </div>

      <div>
        <div className="mb-6">
          <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
            Your Agents
          </h2>
          <p className="text-muted-foreground text-sm font-mono">
            {agents.length} agents configured
          </p>
        </div>

        {agents.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-12 text-center">
            <p className="font-serif text-lg text-foreground mb-2">No agents yet</p>
            <p className="font-mono text-sm text-muted-foreground">
              Create your first voice agent to get started.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
              <AgentCard
                key={agent.id}
                id={agent.id}
                name={agent.name}
                description={agent.description || 'No description provided'}
                status={normalizeStatus(agent.status)}
                callsToday={agent.totalCalls ?? 0}
                accuracy={Math.round(agent.successRate ?? 0)}
                voices={agent.voiceType ? [agent.voiceType] : undefined}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
