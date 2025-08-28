"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Line, LineChart, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"

interface PerformanceChartProps {
  timeRange: string
}

export function PerformanceChart({ timeRange }: PerformanceChartProps) {
  const data = [
    { date: "Jan 1", successRate: 92, responseTime: 2.8, satisfaction: 4.5 },
    { date: "Jan 2", successRate: 94, responseTime: 2.5, satisfaction: 4.6 },
    { date: "Jan 3", successRate: 91, responseTime: 2.9, satisfaction: 4.4 },
    { date: "Jan 4", successRate: 96, responseTime: 2.2, satisfaction: 4.8 },
    { date: "Jan 5", successRate: 93, responseTime: 2.6, satisfaction: 4.7 },
    { date: "Jan 6", successRate: 95, responseTime: 2.1, satisfaction: 4.9 },
    { date: "Jan 7", successRate: 94, responseTime: 2.3, satisfaction: 4.7 },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Trends</CardTitle>
        <CardDescription>Success rate and response time over time</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            successRate: {
              label: "Success Rate (%)",
              color: "hsl(var(--chart-1))",
            },
            responseTime: {
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
                dataKey="successRate"
                stroke="var(--color-successRate)"
                strokeWidth={2}
                dot={{ fill: "var(--color-successRate)" }}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="responseTime"
                stroke="var(--color-responseTime)"
                strokeWidth={2}
                dot={{ fill: "var(--color-responseTime)" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
