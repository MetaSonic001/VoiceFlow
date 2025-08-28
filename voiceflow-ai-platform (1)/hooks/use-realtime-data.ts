"use client"

import { useState, useEffect } from "react"

interface RealtimeMetrics {
  activeCalls: number
  activeChats: number
  queuedInteractions: number
  onlineAgents: number
  avgResponseTime: number
  successRate: number
}

export function useRealtimeData() {
  const [realtimeMetrics, setRealtimeMetrics] = useState<RealtimeMetrics>({
    activeCalls: 8,
    activeChats: 12,
    queuedInteractions: 3,
    onlineAgents: 3,
    avgResponseTime: 2.1,
    successRate: 92,
  })
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    console.log("[v0] Establishing WebSocket connection for real-time data")

    // Simulate connection delay
    const connectTimeout = setTimeout(() => {
      setIsConnected(true)
      console.log("[v0] WebSocket connected successfully")
    }, 2000)

    // Simulate real-time updates every 5 seconds
    const updateInterval = setInterval(() => {
      if (isConnected) {
        setRealtimeMetrics((prev) => ({
          activeCalls: Math.max(0, prev.activeCalls + Math.floor(Math.random() * 3) - 1),
          activeChats: Math.max(0, prev.activeChats + Math.floor(Math.random() * 4) - 2),
          queuedInteractions: Math.max(0, Math.floor(Math.random() * 6)),
          onlineAgents: Math.max(1, Math.min(5, prev.onlineAgents + Math.floor(Math.random() * 3) - 1)),
          avgResponseTime: Math.round((Math.random() * 2 + 1.5) * 10) / 10,
          successRate: Math.round((Math.random() * 10 + 85) * 10) / 10,
        }))
      }
    }, 5000)

    return () => {
      clearTimeout(connectTimeout)
      clearInterval(updateInterval)
      console.log("[v0] WebSocket connection closed")
    }
  }, [isConnected])

  return { realtimeMetrics, isConnected }
}
