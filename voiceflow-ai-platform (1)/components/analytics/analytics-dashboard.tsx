"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { MetricsChart } from "@/components/analytics/metrics-chart"
import { PerformanceChart } from "@/components/analytics/performance-chart"
import { AgentComparison } from "@/components/analytics/agent-comparison"
import { RealtimeMetrics } from "@/components/analytics/realtime-metrics"
import { TrendingUp, TrendingDown, Phone, MessageSquare, Clock, Users, Download } from "lucide-react"

export function AnalyticsDashboard() {
  const [timeRange, setTimeRange] = useState("7d")
  const [selectedAgent, setSelectedAgent] = useState("all")

  // Mock analytics data
  const overviewMetrics = [
    {
      title: "Total Interactions",
      value: "12,847",
      change: "+15.2%",
      trend: "up",
      icon: Users,
      description: "Calls and chats combined",
    },
    {
      title: "Success Rate",
      value: "94.2%",
      change: "+2.1%",
      trend: "up",
      icon: TrendingUp,
      description: "Successfully resolved queries",
    },
    {
      title: "Avg Response Time",
      value: "2.1s",
      change: "-0.3s",
      trend: "up",
      icon: Clock,
      description: "Average time to first response",
    },
    {
      title: "Customer Satisfaction",
      value: "4.7/5",
      change: "+0.2",
      trend: "up",
      icon: TrendingUp,
      description: "Based on post-interaction surveys",
    },
  ]

  const topIssues = [
    { issue: "Password Reset", count: 234, percentage: 18.2 },
    { issue: "Billing Questions", count: 189, percentage: 14.7 },
    { issue: "Product Information", count: 156, percentage: 12.1 },
    { issue: "Technical Support", count: 134, percentage: 10.4 },
    { issue: "Account Setup", count: 98, percentage: 7.6 },
  ]

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
                <p className="text-muted-foreground">Monitor performance and gain insights into your AI agents</p>
              </div>
              <div className="flex items-center space-x-2">
                <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Agents</SelectItem>
                    <SelectItem value="agent-1">Customer Support Assistant</SelectItem>
                    <SelectItem value="agent-2">Sales Qualifier</SelectItem>
                    <SelectItem value="agent-3">HR Assistant</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={timeRange} onValueChange={setTimeRange}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="24h">Last 24h</SelectItem>
                    <SelectItem value="7d">Last 7 days</SelectItem>
                    <SelectItem value="30d">Last 30 days</SelectItem>
                    <SelectItem value="90d">Last 90 days</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
              </div>
            </div>

            {/* Real-time Metrics */}
            <RealtimeMetrics />

            {/* Overview Metrics */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
              {overviewMetrics.map((metric) => (
                <Card key={metric.title}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium text-muted-foreground">{metric.title}</CardTitle>
                      <metric.icon className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{metric.value}</div>
                    <div className="flex items-center space-x-1 mt-1">
                      {metric.trend === "up" ? (
                        <TrendingUp className="w-3 h-3 text-green-500" />
                      ) : (
                        <TrendingDown className="w-3 h-3 text-red-500" />
                      )}
                      <span className={`text-xs ${metric.trend === "up" ? "text-green-600" : "text-red-600"}`}>
                        {metric.change}
                      </span>
                      <span className="text-xs text-muted-foreground">vs last period</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{metric.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid lg:grid-cols-3 gap-6 mb-6">
              {/* Interaction Volume Chart */}
              <div className="lg:col-span-2">
                <MetricsChart timeRange={timeRange} />
              </div>

              {/* Top Issues */}
              <Card>
                <CardHeader>
                  <CardTitle>Top Issues</CardTitle>
                  <CardDescription>Most common customer queries</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {topIssues.map((issue, index) => (
                    <div key={issue.issue} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div className="w-6 h-6 bg-accent text-accent-foreground rounded text-xs flex items-center justify-center">
                          {index + 1}
                        </div>
                        <span className="text-sm font-medium">{issue.issue}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{issue.count}</div>
                        <div className="text-xs text-muted-foreground">{issue.percentage}%</div>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 mb-6">
              {/* Performance Trends */}
              <PerformanceChart timeRange={timeRange} />

              {/* Agent Comparison */}
              <AgentComparison />
            </div>

            {/* Channel Performance */}
            <Card>
              <CardHeader>
                <CardTitle>Channel Performance</CardTitle>
                <CardDescription>Performance breakdown by communication channel</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <Phone className="w-8 h-8 text-accent mx-auto mb-2" />
                    <h3 className="font-medium">Phone Calls</h3>
                    <div className="text-2xl font-bold mt-1">8,234</div>
                    <div className="text-sm text-muted-foreground">Avg duration: 4m 32s</div>
                    <Badge variant="secondary" className="mt-2">
                      96% success rate
                    </Badge>
                  </div>
                  <div className="text-center">
                    <MessageSquare className="w-8 h-8 text-accent mx-auto mb-2" />
                    <h3 className="font-medium">Website Chat</h3>
                    <div className="text-2xl font-bold mt-1">4,613</div>
                    <div className="text-sm text-muted-foreground">Avg duration: 2m 18s</div>
                    <Badge variant="secondary" className="mt-2">
                      92% success rate
                    </Badge>
                  </div>
                  <div className="text-center">
                    <MessageSquare className="w-8 h-8 text-accent mx-auto mb-2" />
                    <h3 className="font-medium">WhatsApp</h3>
                    <div className="text-2xl font-bold mt-1">1,456</div>
                    <div className="text-sm text-muted-foreground">Avg duration: 3m 45s</div>
                    <Badge variant="secondary" className="mt-2">
                      89% success rate
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
