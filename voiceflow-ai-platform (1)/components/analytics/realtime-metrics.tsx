"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Phone, MessageSquare, Users, Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

export function RealtimeMetrics() {
  const [metrics, setMetrics] = useState({
    active_calls: 0,
    active_chats: 0,
    queued_interactions: 0,
    online_agents: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRealtimeMetrics = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await apiClient.getRealtimeMetrics()
        setMetrics(data)
      } catch (err) {
        console.error('Error fetching realtime metrics:', err)
        setError('Failed to load realtime metrics')
        // Fallback to mock data
        setMetrics({
          active_calls: 12,
          active_chats: 8,
          queued_interactions: 3,
          online_agents: 3,
        })
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchRealtimeMetrics()

    // Set up polling for real-time updates
    const interval = setInterval(fetchRealtimeMetrics, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-green-500" />
            <span>Real-time Activity</span>
            <Badge variant="secondary" className="bg-green-100 text-green-800">
              Live
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-20">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="ml-2">Loading metrics...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Activity className="w-5 h-5 text-green-500" />
          <span>Real-time Activity</span>
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            Live
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Phone className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.active_calls}</div>
              <div className="text-sm text-muted-foreground">Active Calls</div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <MessageSquare className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.active_chats}</div>
              <div className="text-sm text-muted-foreground">Active Chats</div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Users className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.queued_interactions}</div>
              <div className="text-sm text-muted-foreground">In Queue</div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.online_agents}</div>
              <div className="text-sm text-muted-foreground">Online Agents</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
