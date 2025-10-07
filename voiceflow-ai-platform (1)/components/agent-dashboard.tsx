"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { AgentCard } from "@/components/dashboard/agent-card"
import MotionWrapper, { containerVariants } from '@/components/ui/MotionWrapper'
import { motion } from 'framer-motion'
import { AgentDetails } from "@/components/dashboard/agent-details"
import { OnboardingWizard } from "@/components/dashboard/onboarding-wizard"
import { LiveActivityFeed } from "@/components/dashboard/live-activity-feed"
import { RealtimeMetrics } from "@/components/dashboard/realtime-metrics"
import { LiveConversations } from "@/components/dashboard/live-conversations"
import { QuickActions } from "@/components/dashboard/quick-actions"
import { Search, Plus, Filter, Activity, Phone, MessageCircle, Users, TrendingUp } from "lucide-react"
import { apiClient } from '@/lib/api-client'

const mockAgents = [
  {
    id: "agent-1",
    name: "Customer Support Assistant",
    role: "Customer Support",
    status: "active" as const,
    channels: ["phone", "chat"],
    phoneNumber: "+1 (555) 123-4567",
    totalCalls: 1247,
    totalChats: 892,
    successRate: 94,
    avgResponseTime: "2.3s",
    lastActive: "2 minutes ago",
    createdAt: "2024-01-15",
    currentCalls: 3,
    currentChats: 7,
    todayInteractions: 45,
  },
  {
    id: "agent-2",
    name: "Sales Qualifier",
    role: "Sales & Lead Qualification",
    status: "active" as const,
    channels: ["phone", "whatsapp"],
    phoneNumber: "+1 (555) 123-4568",
    totalCalls: 456,
    totalChats: 234,
    successRate: 87,
    avgResponseTime: "1.8s",
    lastActive: "5 minutes ago",
    createdAt: "2024-01-20",
    currentCalls: 1,
    currentChats: 2,
    todayInteractions: 23,
  },
  {
    id: "agent-3",
    name: "HR Assistant",
    role: "Internal HR Helpdesk",
    status: "paused" as const,
    channels: ["chat", "email"],
    phoneNumber: null,
    totalCalls: 0,
    totalChats: 156,
    successRate: 91,
    avgResponseTime: "3.1s",
    lastActive: "1 hour ago",
    createdAt: "2024-01-25",
    currentCalls: 0,
    currentChats: 0,
    todayInteractions: 0,
  },
]

export function AgentDashboard() {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [agents, setAgents] = useState(mockAgents)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Mock realtime metrics since we removed the backend dependency
  const realtimeMetrics = {
    totalCalls: 156,
    activeCalls: 8,
    totalChats: 89,
    activeChats: 12,
    successRate: 94.2,
    avgResponseTime: 2.1
  }
  const isConnected = true

  useEffect(() => {
    loadAgents()
    checkOnboardingStatus()
  }, [])

  const loadAgents = async () => {
    try {
      setLoading(true)
      setError(null)
      // Simulate API call delay and use mock data
      await new Promise(resolve => setTimeout(resolve, 500))
      setAgents(mockAgents)
    } catch (err) {
      console.error("[v0] Failed to load agents:", err)
      setError("Failed to load agents. Using demo data.")
      // Keep using mock data on error
      setAgents(mockAgents)
    } finally {
      setLoading(false)
    }
  }

  const [showResumeBanner, setShowResumeBanner] = useState(false)
  const [resumeAgentName, setResumeAgentName] = useState<string | null>(null)
  const [resumeAgentId, setResumeAgentId] = useState<string | null>(null)
  const [wizardStartStep, setWizardStartStep] = useState<number | undefined>(undefined)

  const checkOnboardingStatus = async () => {
    try {
      // Query server-side onboarding progress for the current user
      const prog = await apiClient.getOnboardingProgress()
      if (prog?.exists) {
        setShowResumeBanner(true)
        setResumeAgentId(prog.agent_id ? String(prog.agent_id) : null)
        setWizardStartStep(prog.current_step ? Number(prog.current_step) : undefined)
        // If backend provided agent name in status endpoint earlier, try that first
        try {
          const statusRes = await apiClient.getDeploymentStatus(prog.agent_id ? String(prog.agent_id) : '')
          const agentInfo = (statusRes as any)?.agent
          if (agentInfo && agentInfo.name) setResumeAgentName(agentInfo.name)
        } catch (e) {
          // ignore
        }
        // show step if available
        if (prog.current_step) {
          setResumeAgentName((prev) => prev) // keep name as-is
        }
        return
      }

      // No server progress; don't show banner
      setShowResumeBanner(false)
      setResumeAgentName(null)
      setResumeAgentId(null)
    } catch (err) {
      console.warn('[dashboard] onboarding status check failed', err)
    }
  }

  const filteredAgents = agents.filter((agent) => {
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.role.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === "all" || agent.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const selectedAgentData = agents.find((agent) => agent.id === selectedAgent)

  const totalActiveAgents = agents.filter((a) => a.status === "active").length
  const totalCurrentCalls = agents.reduce((sum, agent) => sum + (agent.currentCalls || 0), 0)
  const totalCurrentChats = agents.reduce((sum, agent) => sum + (agent.currentChats || 0), 0)
  const totalTodayInteractions = agents.reduce((sum, agent) => sum + (agent.todayInteractions || 0), 0)

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        {/* Sidebar */}
        <DashboardSidebar />

        {/* Main Content */}
        <div className="flex-1 ml-64">
          <div className="p-6">
            {/* Resume Onboarding Banner (persistent) */}
            {showResumeBanner && (
              <div aria-label="Resume onboarding banner" className="mb-4 p-4 rounded-lg bg-gradient-to-r from-primary/10 to-accent/5 border border-primary/10 flex items-center justify-between">
                <div>
                  <div className="font-semibold">Continue setting up your AI Agent</div>
                  <div className="text-sm text-muted-foreground">We saved your progress — resume onboarding where you left off.</div>
                  {resumeAgentName && (
                    <div className="mt-2 text-sm">
                      <span className="font-medium">Agent:</span> <span className="ml-2">{resumeAgentName}</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button aria-label="Resume onboarding" variant="outline" onClick={() => {
                    // Open the onboarding wizard modal and open at the saved step
                    setShowCreateDialog(true)
                  }}>
                    Continue Onboarding
                  </Button>
                  <Button aria-label="Open full onboarding page" onClick={() => {
                    // Also give a route option to the full onboarding flow page
                    window.location.href = '/onboarding'
                  }}>
                    Open Onboarding Page
                  </Button>
                </div>
              </div>
            )}
            {!selectedAgent ? (
              <>
                {/* Header with Real-time Status */}
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="flex items-center gap-3">
                      <h1 className="text-3xl font-bold">AI Agents</h1>
                      <Badge variant={isConnected ? "default" : "destructive"} className="flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        {isConnected ? "Live" : "Offline"}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground">Manage and monitor your conversational AI agents</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <QuickActions />
                    <Button onClick={() => setShowCreateDialog(true)}>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Agent
                    </Button>
                  </div>
                </div>

                {/* Real-time Metrics Row */}
                <div className="grid md:grid-cols-6 gap-4 mb-6">
                  <Card className="hover:shadow-md hover:scale-102 transition-transform duration-150">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <Users className="w-4 h-4" />
                        Active Agents
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{totalActiveAgents}</div>
                      <p className="text-xs text-muted-foreground">of {agents.length} total</p>
                    </CardContent>
                  </Card>

                  <Card className="hover:shadow-md hover:scale-102 transition-transform duration-150">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <Phone className="w-4 h-4" />
                        Live Calls
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-green-600">{totalCurrentCalls}</div>
                      <p className="text-xs text-muted-foreground">active now</p>
                    </CardContent>
                  </Card>

                  <Card className="hover:shadow-md hover:scale-102 transition-transform duration-150">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <MessageCircle className="w-4 h-4" />
                        Live Chats
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-blue-600">{totalCurrentChats}</div>
                      <p className="text-xs text-muted-foreground">active now</p>
                    </CardContent>
                  </Card>

                  <Card className="hover:shadow-md hover:scale-102 transition-transform duration-150">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        Today
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{totalTodayInteractions}</div>
                      <p className="text-xs text-green-600">+12% vs yesterday</p>
                    </CardContent>
                  </Card>

                  <Card className="hover:shadow-md hover:scale-102 transition-transform duration-150">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">Avg Success Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {Math.round(agents.reduce((sum, agent) => sum + agent.successRate, 0) / agents.length)}%
                      </div>
                      <p className="text-xs text-green-600">+2% from last month</p>
                    </CardContent>
                  </Card>

                  <Card className="hover:shadow-md hover:scale-102 transition-transform duration-150">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">Avg Response</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">2.1s</div>
                      <p className="text-xs text-green-600">-0.3s improvement</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Real-time Activity Section */}
                <div className="grid lg:grid-cols-3 gap-6 mb-6">
                  <div className="lg:col-span-2">
                    <RealtimeMetrics />
                  </div>
                  <div>
                    <LiveActivityFeed />
                  </div>
                </div>

                {/* Live Conversations Section */}
                <div className="mb-6">
                  <LiveConversations />
                </div>

                {/* Filters */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <div className="relative flex-1 max-w-sm">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="Search agents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-40">
                        <Filter className="w-4 h-4 mr-2" />
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="active">Active</SelectItem>
                        <SelectItem value="paused">Paused</SelectItem>
                        <SelectItem value="draft">Draft</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {error && (
                    <Badge variant="destructive" className="ml-4">
                      {error}
                    </Badge>
                  )}
                </div>

                {/* Agents Grid */}
                {loading ? (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3].map((i) => (
                      <Card key={i} className="animate-pulse">
                        <CardHeader>
                          <div className="h-4 bg-muted rounded w-3/4"></div>
                          <div className="h-3 bg-muted rounded w-1/2"></div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="h-3 bg-muted rounded"></div>
                            <div className="h-3 bg-muted rounded w-2/3"></div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <motion.div variants={containerVariants} initial="hidden" animate="show" exit="exit" className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredAgents.map((agent) => (
                      <AgentCard key={agent.id} agent={agent} onSelect={() => setSelectedAgent(agent.id)} />
                    ))}
                  </motion.div>
                )}

                {filteredAgents.length === 0 && !loading && (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">No agents found matching your criteria.</p>
                  </div>
                )}
              </>
            ) : (
              <AgentDetails agent={selectedAgentData!} onBack={() => setSelectedAgent(null)} />
            )}
          </div>
        </div>
      </div>

      <OnboardingWizard 
        open={showCreateDialog} 
        onOpenChange={setShowCreateDialog}
        startStep={wizardStartStep}
        onComplete={() => {
          // Refresh agents list or add new agent to state
          console.log('Agent creation completed')
            // Clear any saved onboarding progress server-side so the resume banner hides
            ;(async () => {
              try { await apiClient.deleteOnboardingProgress() } catch (e) {}
              setShowResumeBanner(false)
              setWizardStartStep(undefined)
              loadAgents()
            })()
        }}
      />
    </div>
  )
}
