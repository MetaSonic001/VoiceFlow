"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"

export function AgentComparison() {
  const agents = [
    {
      name: "Customer Support Assistant",
      interactions: 1247,
      successRate: 94,
      avgResponseTime: 2.3,
      status: "active",
    },
    {
      name: "Sales Qualifier",
      interactions: 456,
      successRate: 87,
      avgResponseTime: 1.8,
      status: "active",
    },
    {
      name: "HR Assistant",
      interactions: 156,
      successRate: 91,
      avgResponseTime: 3.1,
      status: "paused",
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Comparison</CardTitle>
        <CardDescription>Performance comparison across all agents</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {agents.map((agent) => (
          <div key={agent.name} className="space-y-2">
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
                <span>{agent.successRate}%</span>
              </div>
              <Progress value={agent.successRate} className="h-2" />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Avg Response: {agent.avgResponseTime}s</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
