import { KPICard } from '@/components/kpi-card'
import { AgentCard } from '@/components/agent-card'
import { Users, Phone, BarChart3, Clock } from 'lucide-react'

// Mock data
const mockAgents = [
  {
    id: '1',
    name: 'Customer Support Agent',
    description: 'Handles inbound customer calls and inquiries with AI-powered responses',
    status: 'active' as const,
    callsToday: 245,
    accuracy: 94,
    voices: ['Sarah', 'Alex'],
  },
  {
    id: '2',
    name: 'Sales Outreach Bot',
    description: 'Proactive outbound calling for lead generation and follow-ups',
    status: 'active' as const,
    callsToday: 189,
    accuracy: 88,
    voices: ['James'],
  },
  {
    id: '3',
    name: 'Appointment Scheduler',
    description: 'Automatically books and confirms appointments with customers',
    status: 'paused' as const,
    callsToday: 0,
    accuracy: 92,
    voices: ['Emma'],
  },
  {
    id: '4',
    name: 'Survey Assistant',
    description: 'Conducts voice surveys and collects customer feedback',
    status: 'inactive' as const,
    callsToday: 0,
    accuracy: 85,
    voices: ['David'],
  },
]

export default function DashboardPage() {
  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          AI Agents Dashboard
        </h1>
        <p className="text-muted-foreground font-mono">
          Manage and monitor your voice AI agents
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          icon={Phone}
          label="Active Agents"
          value={2}
          color="accent"
          trend={{ value: 25, isPositive: true }}
        />
        <KPICard
          icon={Clock}
          label="Total Calls Today"
          value={434}
          color="success"
          trend={{ value: 12, isPositive: true }}
        />
        <KPICard
          icon={BarChart3}
          label="Avg Accuracy"
          value="89.75"
          unit="%"
          color="default"
          trend={{ value: 3, isPositive: true }}
        />
        <KPICard
          icon={Users}
          label="Total Agents"
          value={4}
          color="default"
          trend={{ value: 0, isPositive: false }}
        />
      </div>

      {/* Agents Grid */}
      <div>
        <div className="mb-6">
          <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
            Your Agents
          </h2>
          <p className="text-muted-foreground text-sm font-mono">
            {mockAgents.length} agents configured
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mockAgents.map((agent) => (
            <AgentCard key={agent.id} {...agent} />
          ))}
        </div>
      </div>
    </div>
  )
}
