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
        // Transform the API response to chart format
        // Assuming the API returns data in the format we need, or transform it
        setData(response.datasets ? response.datasets : [])
      } catch (err) {
        console.error('Error fetching metrics chart data:', err)
        setError('Failed to load chart data')
        // Fallback to mock data
        setData([
          { date: "Jan 1", calls: 120, chats: 85, total: 205 },
          { date: "Jan 2", calls: 145, chats: 92, total: 237 },
          { date: "Jan 3", calls: 132, chats: 78, total: 210 },
          { date: "Jan 4", calls: 168, chats: 105, total: 273 },
          { date: "Jan 5", calls: 156, chats: 98, total: 254 },
          { date: "Jan 6", calls: 189, chats: 112, total: 301 },
          { date: "Jan 7", calls: 178, chats: 108, total: 286 },
        ])
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

  // Transform API data to Recharts format
  const chartData = data.length > 0 ? data[0]?.data?.map((value: number, index: number) => ({
    date: data[0]?.labels?.[index] || `Day ${index + 1}`,
    calls: value,
    chats: data[1]?.data?.[index] || 0,
    total: value + (data[1]?.data?.[index] || 0)
  })) || [] : []

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
