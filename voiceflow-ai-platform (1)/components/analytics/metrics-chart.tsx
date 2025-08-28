"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { XAxis, YAxis, CartesianGrid, ResponsiveContainer, Area, AreaChart } from "recharts"

interface MetricsChartProps {
  timeRange: string
}

export function MetricsChart({ timeRange }: MetricsChartProps) {
  // Mock data based on time range
  const generateData = () => {
    const baseData = [
      { date: "Jan 1", calls: 120, chats: 85, total: 205 },
      { date: "Jan 2", calls: 145, chats: 92, total: 237 },
      { date: "Jan 3", calls: 132, chats: 78, total: 210 },
      { date: "Jan 4", calls: 168, chats: 105, total: 273 },
      { date: "Jan 5", calls: 156, chats: 98, total: 254 },
      { date: "Jan 6", calls: 189, chats: 112, total: 301 },
      { date: "Jan 7", calls: 178, chats: 108, total: 286 },
    ]
    return baseData
  }

  const data = generateData()

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
            <AreaChart data={data}>
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
