"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { XAxis, YAxis, CartesianGrid, ResponsiveContainer, Area, AreaChart } from "recharts"
import { Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface MetricsChartProps {
  timeRange: string
  agentId?: string
}

export function MetricsChart({ timeRange, agentId }: MetricsChartProps) {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetricsData = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await apiClient.getMetricsChart(timeRange, agentId)
        // Backend returns { data: [{ date, calls, chats, total }] }
        setData(response.data || [])
      } catch (err) {
        console.error('Error fetching metrics chart data:', err)
        setError('Failed to load chart data')
        setData([])
      } finally {
        setLoading(false)
      }
    }

    fetchMetricsData()
  }, [timeRange, agentId])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Interaction Volume</CardTitle>
          <CardDescription>Daily calls and chats over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px]">
            <Loader2 className="w-6 h-6 animate-spin" />
            <span className="ml-2">Loading chart data...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error && !data.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Interaction Volume</CardTitle>
          <CardDescription>Daily calls and chats over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px]">
            <p className="text-red-600">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Data is already in { date, calls, chats, total } format from the API
  const chartData = data

  return (
    <Card>
      <CardHeader>
        <CardTitle>Interaction Volume</CardTitle>
        <CardDescription>Daily calls and chats over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            calls: {
              label: "Phone Calls",
              color: "hsl(var(--chart-1))",
            },
            chats: {
              label: "Chat Messages",
              color: "hsl(var(--chart-2))",
            },
            total: {
              label: "Total Interactions",
              color: "hsl(var(--chart-3))",
            },
          }}
          className="h-[300px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Area
                type="monotone"
                dataKey="calls"
                stackId="1"
                stroke="var(--color-calls)"
                fill="var(--color-calls)"
                fillOpacity={0.6}
              />
              <Area
                type="monotone"
                dataKey="chats"
                stackId="1"
                stroke="var(--color-chats)"
                fill="var(--color-chats)"
                fillOpacity={0.6}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
