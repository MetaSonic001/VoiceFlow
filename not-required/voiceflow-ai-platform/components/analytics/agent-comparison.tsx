"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

export function AgentComparison() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAgentComparison = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await apiClient.getAgentComparison()
        // Map backend shape to component shape
        const mapped = (data.agents || []).map((a: any) => ({
          id: a.agentId,
          name: a.agentName,
          interactions: a.totalInteractions ?? 0,
          successRate: a.successRate ?? 0,
          avgResponseTime: a.avgResponseTime ?? 0,
          status: 'active',
        }))
        setAgents(mapped)
      } catch (err) {
        console.error('Error fetching agent comparison data:', err)
        setError('Failed to load agent comparison data')
        setAgents([])
      } finally {
        setLoading(false)
      }
    }

    fetchAgentComparison()
  }, [])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Comparison</CardTitle>
          <CardDescription>Performance comparison across all agents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin" />
            <span className="ml-2">Loading agent data...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error && !agents.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Comparison</CardTitle>
          <CardDescription>Performance comparison across all agents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32">
            <p className="text-red-600">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Comparison</CardTitle>
        <CardDescription>Performance comparison across all agents</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {agents.map((agent: any) => (
          <div key={agent.name || agent.id} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="font-medium text-sm">{agent.name}</span>
                <Badge variant={agent.status === "active" ? "secondary" : "outline"} className="text-xs">
                  {agent.status}
                </Badge>
              </div>
              <span className="text-sm text-muted-foreground">{agent.interactions} interactions</span>
            </div>
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span>Success Rate</span>
                <span>{agent.success_rate || agent.successRate}%</span>
              </div>
              <Progress value={agent.success_rate || agent.successRate} className="h-2" />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Avg Response: {agent.avg_response_time || agent.avgResponseTime}s</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
