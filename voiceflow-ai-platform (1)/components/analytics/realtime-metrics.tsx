"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Phone, MessageSquare, Users } from "lucide-react"

export function RealtimeMetrics() {
  const [metrics, setMetrics] = useState({
    activeCalls: 12,
    activeChats: 8,
    queuedInteractions: 3,
    onlineAgents: 3,
  })

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((prev) => ({
        activeCalls: Math.max(0, prev.activeCalls + Math.floor(Math.random() * 3) - 1),
        activeChats: Math.max(0, prev.activeChats + Math.floor(Math.random() * 3) - 1),
        queuedInteractions: Math.max(0, prev.queuedInteractions + Math.floor(Math.random() * 2) - 1),
        onlineAgents: 3, // Keep constant for demo
      }))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

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
              <div className="text-2xl font-bold">{metrics.activeCalls}</div>
              <div className="text-sm text-muted-foreground">Active Calls</div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <MessageSquare className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.activeChats}</div>
              <div className="text-sm text-muted-foreground">Active Chats</div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Users className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.queuedInteractions}</div>
              <div className="text-sm text-muted-foreground">In Queue</div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Activity className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold">{metrics.onlineAgents}</div>
              <div className="text-sm text-muted-foreground">Online Agents</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
