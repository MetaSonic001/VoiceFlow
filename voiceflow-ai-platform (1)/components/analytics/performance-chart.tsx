"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface PerformanceChartProps {
  timeRange: string
  agentId?: string
}

export function PerformanceChart({ timeRange, agentId }: PerformanceChartProps) {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPerformanceData = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await apiClient.getPerformanceData(timeRange, agentId)
        setData(response.data || [])
      } catch (err) {
        console.error('Error fetching performance data:', err)
        setError('Failed to load performance data')
        // Fallback to mock data
        setData([
          { date: "Jan 1", successRate: 92, responseTime: 2.8, satisfaction: 4.5 },
          { date: "Jan 2", successRate: 94, responseTime: 2.5, satisfaction: 4.6 },
          { date: "Jan 3", successRate: 91, responseTime: 2.9, satisfaction: 4.4 },
          { date: "Jan 4", successRate: 96, responseTime: 2.2, satisfaction: 4.8 },
          { date: "Jan 5", successRate: 93, responseTime: 2.6, satisfaction: 4.7 },
          { date: "Jan 6", successRate: 95, responseTime: 2.1, satisfaction: 4.9 },
          { date: "Jan 7", successRate: 94, responseTime: 2.3, satisfaction: 4.7 },
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchPerformanceData()
  }, [timeRange, agentId])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Trends</CardTitle>
          <CardDescription>Success rate and response time over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px]">
            <Loader2 className="w-6 h-6 animate-spin" />
            <span className="ml-2">Loading performance data...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error && !data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Performance Trends</CardTitle>
          <CardDescription>Success rate and response time over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px]">
            <p className="text-red-600">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Trends</CardTitle>
        <CardDescription>Success rate and response time over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            success_rate: {
              label: "Success Rate (%)",
              color: "hsl(var(--chart-1))",
            },
            response_time: {
              label: "Response Time (s)",
              color: "hsl(var(--chart-2))",
            },
          }}
          className="h-[300px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" domain={[85, 100]} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 5]} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="success_rate"
                stroke="var(--color-success_rate)"
                strokeWidth={2}
                dot={{ fill: "var(--color-success_rate)" }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="response_time"
                stroke="var(--color-response_time)"
                strokeWidth={2}
                dot={{ fill: "var(--color-response_time)" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
