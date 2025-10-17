"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  Activity,
  Server,
  Database,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Cpu,
  HardDrive,
  Wifi,
  Users,
  MessageSquare,
  Phone
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface SystemMetrics {
  uptime: string
  cpu: number
  memory: number
  disk: number
  network: {
    requests: number
    latency: number
  }
  services: {
    name: string
    status: 'healthy' | 'warning' | 'error'
    uptime: string
    responseTime: number
  }[]
  queues: {
    name: string
    pending: number
    processing: number
    completed: number
  }[]
}

export default function SystemHealthPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  useEffect(() => {
    loadSystemMetrics()

    // Update metrics every 30 seconds
    const interval = setInterval(() => {
      loadSystemMetrics()
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  const loadSystemMetrics = async () => {
    try {
      setLoading(true)
      // This would call a system health API endpoint
      // const data = await apiClient.getSystemHealth()
      // For now, using mock data
      const mockMetrics: SystemMetrics = {
        uptime: "7d 14h 32m",
        cpu: 45,
        memory: 67,
        disk: 23,
        network: {
          requests: 1250,
          latency: 45
        },
        services: [
          { name: "API Server", status: "healthy", uptime: "99.9%", responseTime: 23 },
          { name: "Database", status: "healthy", uptime: "99.8%", responseTime: 12 },
          { name: "Redis Cache", status: "healthy", uptime: "99.7%", responseTime: 5 },
          { name: "Worker Queue", status: "warning", uptime: "98.5%", responseTime: 89 },
          { name: "File Storage", status: "healthy", uptime: "99.9%", responseTime: 34 },
          { name: "Email Service", status: "error", uptime: "95.2%", responseTime: 150 }
        ],
        queues: [
          { name: "Message Processing", pending: 12, processing: 3, completed: 1247 },
          { name: "Document Ingestion", pending: 5, processing: 2, completed: 456 },
          { name: "Analytics Jobs", pending: 8, processing: 1, completed: 234 },
          { name: "Notification Queue", pending: 0, processing: 0, completed: 89 }
        ]
      }
      setMetrics(mockMetrics)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to load system metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case 'error': return <XCircle className="w-4 h-4 text-red-500" />
      default: return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'healthy': return 'default'
      case 'warning': return 'secondary'
      case 'error': return 'destructive'
      default: return 'outline'
    }
  }

  if (loading && !metrics) {
    return (
      <div className="min-h-screen bg-background">
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-2">Loading system health...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">System Health</h1>
                <p className="text-muted-foreground">Monitor system performance and service status</p>
              </div>
              <div className="text-sm text-muted-foreground">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </div>
            </div>

            {/* System Overview */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center">
                    <Server className="w-4 h-4 mr-2" />
                    Uptime
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.uptime}</div>
                  <p className="text-xs text-muted-foreground">System running time</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center">
                    <Cpu className="w-4 h-4 mr-2" />
                    CPU Usage
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.cpu}%</div>
                  <Progress value={metrics?.cpu} className="mt-2" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center">
                    <Database className="w-4 h-4 mr-2" />
                    Memory
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.memory}%</div>
                  <Progress value={metrics?.memory} className="mt-2" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center">
                    <HardDrive className="w-4 h-4 mr-2" />
                    Disk Usage
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{metrics?.disk}%</div>
                  <Progress value={metrics?.disk} className="mt-2" />
                </CardContent>
              </Card>
            </div>

            {/* Network & Performance */}
            <div className="grid md:grid-cols-2 gap-6 mb-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Wifi className="w-5 h-5 mr-2" />
                    Network Performance
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Requests/min</span>
                    <span className="text-2xl font-bold">{metrics?.network.requests}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Avg Latency</span>
                    <span className="text-2xl font-bold">{metrics?.network.latency}ms</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Activity className="w-5 h-5 mr-2" />
                    Active Connections
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium flex items-center">
                      <Users className="w-4 h-4 mr-1" />
                      Users
                    </span>
                    <span className="text-2xl font-bold">1,247</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium flex items-center">
                      <MessageSquare className="w-4 h-4 mr-1" />
                      Chats
                    </span>
                    <span className="text-2xl font-bold">89</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium flex items-center">
                      <Phone className="w-4 h-4 mr-1" />
                      Calls
                    </span>
                    <span className="text-2xl font-bold">23</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Service Status */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Service Status</CardTitle>
                <CardDescription>Health status of all system services</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {metrics?.services.map((service) => (
                    <div key={service.name} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(service.status)}
                        <div>
                          <p className="font-medium text-sm">{service.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {service.uptime} uptime • {service.responseTime}ms
                          </p>
                        </div>
                      </div>
                      <Badge variant={getStatusBadgeVariant(service.status)}>
                        {service.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Queue Status */}
            <Card>
              <CardHeader>
                <CardTitle>Queue Status</CardTitle>
                <CardDescription>Background job queues and processing status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {metrics?.queues.map((queue) => (
                    <div key={queue.name} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">{queue.name}</h4>
                        <div className="flex space-x-4 text-sm">
                          <span className="text-yellow-600">Pending: {queue.pending}</span>
                          <span className="text-blue-600">Processing: {queue.processing}</span>
                          <span className="text-green-600">Completed: {queue.completed}</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-yellow-400 h-2 rounded-l-full"
                          style={{ width: `${(queue.pending / (queue.pending + queue.processing + queue.completed)) * 100}%` }}
                        ></div>
                        <div
                          className="bg-blue-400 h-2"
                          style={{ width: `${(queue.processing / (queue.pending + queue.processing + queue.completed)) * 100}%` }}
                        ></div>
                        <div
                          className="bg-green-400 h-2 rounded-r-full"
                          style={{ width: `${(queue.completed / (queue.pending + queue.processing + queue.completed)) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
        </div>
      </div>
    )
  }