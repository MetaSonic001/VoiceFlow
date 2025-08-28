"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts"
import { TrendingUp, TrendingDown, Activity, Clock } from "lucide-react"

interface MetricData {
  timestamp: string
  calls: number
  chats: number
  responseTime: number
  successRate: number
}

const generateMetricData = (): MetricData[] => {
  const data: MetricData[] = []
  const now = new Date()

  for (let i = 29; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 60000) // Every minute for last 30 minutes
    data.push({
      timestamp: timestamp.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
      calls: Math.floor(Math.random() * 10) + 2,
      chats: Math.floor(Math.random() * 15) + 5,
      responseTime: Math.random() * 2 + 1, // 1-3 seconds
      successRate: Math.random() * 10 + 85, // 85-95%
    })
  }

  return data
}

export function RealtimeMetrics() {
  const [metricsData, setMetricsData] = useState<MetricData[]>(generateMetricData())
  const [currentMetrics, setCurrentMetrics] = useState({
    activeCalls: 8,
    activeChats: 12,
    avgResponseTime: 2.1,
    successRate: 92,
    queuedInteractions: 3,
  })

  useEffect(() => {
    const interval = setInterval(() => {
      // Add new data point
      const newDataPoint: MetricData = {
        timestamp: new Date().toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" }),
        calls: Math.floor(Math.random() * 10) + 2,
        chats: Math.floor(Math.random() * 15) + 5,
        responseTime: Math.random() * 2 + 1,
        successRate: Math.random() * 10 + 85,
      }

      setMetricsData((prev) => [...prev.slice(1), newDataPoint])

      // Update current metrics
      setCurrentMetrics((prev) => ({
        activeCalls: Math.max(0, prev.activeCalls + Math.floor(Math.random() * 3) - 1),
        activeChats: Math.max(0, prev.activeChats + Math.floor(Math.random() * 4) - 2),
        avgResponseTime: Math.round((Math.random() * 2 + 1.5) * 10) / 10,
        successRate: Math.round((Math.random() * 10 + 85) * 10) / 10,
        queuedInteractions: Math.max(0, Math.floor(Math.random() * 6)),
      }))
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  const totalInteractions = metricsData[metricsData.length - 1]?.calls + metricsData[metricsData.length - 1]?.chats || 0
  const previousTotal = metricsData[metricsData.length - 2]?.calls + metricsData[metricsData.length - 2]?.chats || 0
  const trend = totalInteractions > previousTotal ? "up" : totalInteractions < previousTotal ? "down" : "stable"

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Real-time Performance
          </span>
          <Badge variant="outline" className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            Live
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Current Status Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{currentMetrics.activeCalls}</div>
            <div className="text-xs text-muted-foreground">Active Calls</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{currentMetrics.activeChats}</div>
            <div className="text-xs text-muted-foreground">Active Chats</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{currentMetrics.avgResponseTime}s</div>
            <div className="text-xs text-muted-foreground">Avg Response</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{currentMetrics.successRate}%</div>
            <div className="text-xs text-muted-foreground">Success Rate</div>
          </div>
        </div>

        {/* Queue Status */}
        {currentMetrics.queuedInteractions > 0 && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-yellow-600" />
                <span className="text-sm font-medium text-yellow-800">
                  {currentMetrics.queuedInteractions} interactions in queue
                </span>
              </div>
              <Badge variant="secondary">Avg wait: 45s</Badge>
            </div>
          </div>
        )}

        {/* Trend Indicator */}
        <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
          <span className="text-sm text-muted-foreground">Current trend</span>
          <div className="flex items-center gap-2">
            {trend === "up" ? (
              <TrendingUp className="w-4 h-4 text-green-600" />
            ) : trend === "down" ? (
              <TrendingDown className="w-4 h-4 text-red-600" />
            ) : (
              <Activity className="w-4 h-4 text-muted-foreground" />
            )}
            <span className="text-sm font-medium">
              {trend === "up" ? "Increasing" : trend === "down" ? "Decreasing" : "Stable"}
            </span>
          </div>
        </div>

        {/* Mini Chart */}
        <div className="h-32">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={metricsData.slice(-15)}>
              <XAxis dataKey="timestamp" hide />
              <YAxis hide />
              <Tooltip
                labelFormatter={(label) => `Time: ${label}`}
                formatter={(value, name) => [
                  name === "calls" ? `${value} calls` : `${value} chats`,
                  name === "calls" ? "Calls" : "Chats",
                ]}
              />
              <Line type="monotone" dataKey="calls" stroke="#3b82f6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="chats" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
