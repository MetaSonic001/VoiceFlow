"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { CallLogDetails } from "@/components/analytics/call-log-details"
import { Search, Filter, Download, Phone, MessageSquare, Clock, Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface CallLog {
  id: string
  type: "phone" | "chat"
  customerInfo: string
  agentName: string
  agentId: string
  startTime: string
  duration: number
  status: string
  resolution: string
  summary: string
  sentiment: string
  tags: string[]
  transcript?: string
}

export function CallLogs() {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [typeFilter, setTypeFilter] = useState("all")
  const [selectedLog, setSelectedLog] = useState<string | null>(null)
  const [callLogs, setCallLogs] = useState<CallLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCallLogs()
  }, [])

  const loadCallLogs = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiClient.getCallLogs()
      setCallLogs(data)
    } catch (err) {
      console.error('Error loading call logs:', err)
      setError('Failed to load call logs')
      // Fallback to mock data
      const mockLogs: CallLog[] = [
        {
          id: "call-001",
          type: "phone",
          customerInfo: "+1 (555) 987-6543",
          agentName: "Customer Support Assistant",
          agentId: "agent-1",
          startTime: "2024-01-15T14:30:25Z",
          duration: 204,
          status: "completed",
          resolution: "resolved",
          summary: "Customer inquiry about product pricing and availability. Provided detailed information about current promotions.",
          sentiment: "positive",
          tags: ["pricing", "product-info"],
        },
        {
          id: "call-002",
          type: "chat",
          customerInfo: "Anonymous User",
          agentName: "Customer Support Assistant",
          agentId: "agent-1",
          startTime: "2024-01-15T14:25:12Z",
          duration: 105,
          status: "completed",
          resolution: "resolved",
          summary: "Password reset assistance. Guided customer through the reset process successfully.",
          sentiment: "neutral",
          tags: ["password-reset", "account"],
        }
      ]
      setCallLogs(mockLogs)
    } finally {
      setLoading(false)
    }
  }

  const filteredLogs = callLogs.filter((log) => {
    const matchesSearch =
      log.customerInfo.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesStatus = statusFilter === "all" || log.status === statusFilter
    const matchesType = typeFilter === "all" || log.type === typeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  const selectedLogData = callLogs.find((log) => log.id === selectedLog)

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800 border-green-200"
      case "escalated":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "failed":
        return "bg-red-100 text-red-800 border-red-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "text-green-600"
      case "negative":
        return "text-red-600"
      case "neutral":
        return "text-gray-600"
      default:
        return "text-gray-600"
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex">
          <DashboardSidebar />
          <div className="flex-1 ml-64">
            <div className="p-6">
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin" />
                <span className="ml-2">Loading call logs...</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex">
          <DashboardSidebar />
          <div className="flex-1 ml-64">
            <div className="p-6">
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <p className="text-red-600 mb-2">{error}</p>
                  <Button onClick={loadCallLogs}>Retry</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (selectedLog && selectedLogData) {
    return <CallLogDetails log={selectedLogData} onBack={() => setSelectedLog(null)} />
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Call Logs</h1>
                <p className="text-muted-foreground">Monitor and analyze all customer interactions</p>
              </div>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Export Logs
              </Button>
            </div>

            {/* Filters */}
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="flex items-center space-x-4">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Search logs..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                  <Select value={typeFilter} onValueChange={setTypeFilter}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="All Types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="phone">Phone Calls</SelectItem>
                      <SelectItem value="chat">Chat Messages</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-40">
                      <Filter className="w-4 h-4 mr-2" />
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="escalated">Escalated</SelectItem>
                      <SelectItem value="failed">Failed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Call Logs Table */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Interactions</CardTitle>
                <CardDescription>{filteredLogs.length} interactions found</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {filteredLogs.map((log) => (
                    <div
                      key={log.id}
                      className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                      onClick={() => setSelectedLog(log.id)}
                    >
                      <div className="flex items-center space-x-4">
                        <div className="p-2 bg-muted rounded">
                          {log.type === "phone" ? <Phone className="w-4 h-4" /> : <MessageSquare className="w-4 h-4" />}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="font-medium">{log.customerInfo}</span>
                            <Badge variant="outline" className="text-xs">
                              {log.agentName}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground line-clamp-1">{log.summary}</p>
                          <div className="flex items-center space-x-4 mt-2">
                            <div className="flex items-center space-x-1 text-xs text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              {log.startTime}
                            </div>
                            <div className="text-xs text-muted-foreground">Duration: {log.duration}</div>
                            <div className={`text-xs font-medium ${getSentimentColor(log.sentiment)}`}>
                              {log.sentiment}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="flex flex-wrap gap-1">
                          {log.tags.slice(0, 2).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {log.tags.length > 2 && (
                            <Badge variant="secondary" className="text-xs">
                              +{log.tags.length - 2}
                            </Badge>
                          )}
                        </div>
                        <Badge className={getStatusColor(log.status)} variant="outline">
                          {log.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>

                {filteredLogs.length === 0 && (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">No interactions found matching your criteria.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
