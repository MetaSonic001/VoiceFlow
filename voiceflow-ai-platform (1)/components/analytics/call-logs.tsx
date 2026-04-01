"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { CallLogDetails } from "@/components/analytics/call-log-details"
import {
  Search,
  Download,
  Phone,
  Clock,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Flag,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

// Matches the Prisma CallLog schema + joined agent name
interface CallLogEntry {
  id: string
  tenantId: string
  agentId: string
  startedAt: string
  endedAt: string | null
  durationSeconds: number | null
  transcript: string
  rating: number | null
  ratingNotes: string | null
  flaggedForRetraining: boolean
  createdAt: string
  agent: { id: string; name: string }
}

// ── Mock data matching the real API shape ─────────────────────────────────
const MOCK_LOGS: CallLogEntry[] = [
  {
    id: "log-001",
    tenantId: "t1",
    agentId: "a1",
    startedAt: "2025-03-28T14:30:25Z",
    endedAt: "2025-03-28T14:33:49Z",
    durationSeconds: 204,
    transcript: JSON.stringify([
      { speaker: "agent", message: "Hello! Thank you for calling. How can I help you today?", timestamp: "14:30:25" },
      { speaker: "customer", message: "Hi, I'm interested in your premium plan. Can you tell me about the pricing?", timestamp: "14:30:32" },
      { speaker: "agent", message: "Our premium plan is $29.99/month and includes unlimited calls, advanced analytics, and priority support.", timestamp: "14:30:45" },
      { speaker: "customer", message: "Are there any current promotions?", timestamp: "14:31:12" },
      { speaker: "agent", message: "Yes! We're offering 20% off for the first 3 months — that's $23.99/month.", timestamp: "14:31:25" },
      { speaker: "customer", message: "Great, how do I sign up?", timestamp: "14:31:45" },
      { speaker: "agent", message: "I can transfer you to sales right now. Thank you for your interest!", timestamp: "14:31:52" },
    ]),
    rating: 1,
    ratingNotes: null,
    flaggedForRetraining: false,
    createdAt: "2025-03-28T14:30:25Z",
    agent: { id: "a1", name: "Support Bot" },
  },
  {
    id: "log-002",
    tenantId: "t1",
    agentId: "a1",
    startedAt: "2025-03-28T10:15:00Z",
    endedAt: "2025-03-28T10:16:45Z",
    durationSeconds: 105,
    transcript: JSON.stringify([
      { speaker: "agent", message: "Hi there! How can I help you?", timestamp: "10:15:00" },
      { speaker: "customer", message: "I forgot my password and can't log in.", timestamp: "10:15:08" },
      { speaker: "agent", message: "No problem. I'll send a password reset link to your email. Can you confirm the email on your account?", timestamp: "10:15:15" },
      { speaker: "customer", message: "It's john@example.com", timestamp: "10:15:25" },
      { speaker: "agent", message: "Done! You should receive a reset link within a minute. Is there anything else?", timestamp: "10:15:35" },
      { speaker: "customer", message: "That's all, thanks!", timestamp: "10:15:42" },
    ]),
    rating: null,
    ratingNotes: null,
    flaggedForRetraining: false,
    createdAt: "2025-03-28T10:15:00Z",
    agent: { id: "a1", name: "Support Bot" },
  },
  {
    id: "log-003",
    tenantId: "t1",
    agentId: "a2",
    startedAt: "2025-03-27T16:00:00Z",
    endedAt: "2025-03-27T16:04:10Z",
    durationSeconds: 250,
    transcript: JSON.stringify([
      { speaker: "agent", message: "Good afternoon! I'm calling from Acme Corp regarding our enterprise solution.", timestamp: "16:00:00" },
      { speaker: "customer", message: "I'm not interested.", timestamp: "16:00:08" },
      { speaker: "agent", message: "I understand. Would you be open to a 2-minute overview? Many companies in your industry have seen 30% efficiency gains.", timestamp: "16:00:15" },
      { speaker: "customer", message: "Fine, go ahead.", timestamp: "16:00:25" },
      { speaker: "agent", message: "Great! Our platform automates customer interactions across phone, chat, and email…", timestamp: "16:00:30" },
    ]),
    rating: -1,
    ratingNotes: "Agent was too pushy",
    flaggedForRetraining: true,
    createdAt: "2025-03-27T16:00:00Z",
    agent: { id: "a2", name: "Sales Caller" },
  },
]

export function CallLogs() {
  const [logs, setLogs] = useState<CallLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)

  // Filters
  const [agentFilter, setAgentFilter] = useState("all")
  const [fromDate, setFromDate] = useState("")
  const [toDate, setToDate] = useState("")

  // Agent list for dropdown
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([])

  // Detail view
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null)

  const LIMIT = 20

  const loadLogs = useCallback(async () => {
    try {
      setLoading(true)
      const params: any = { page, limit: LIMIT }
      if (agentFilter !== "all") params.agentId = agentFilter
      if (fromDate) params.from = fromDate
      if (toDate) params.to = toDate

      const data = await apiClient.getCallLogs(params)
      setLogs(data.logs)
      setTotal(data.total)
      setTotalPages(data.pages || Math.ceil(data.total / LIMIT))
    } catch {
      // Fallback to mock data
      setLogs(MOCK_LOGS)
      setTotal(MOCK_LOGS.length)
      setTotalPages(1)
    } finally {
      setLoading(false)
    }
  }, [page, agentFilter, fromDate, toDate])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  // Load agent list for filter
  useEffect(() => {
    ;(async () => {
      try {
        const res = await apiClient.getAgents({ limit: 100 })
        const raw = Array.isArray(res) ? res : (res as any).agents || []
        const list = raw.map((a: any) => ({ id: a.id, name: a.name }))
        setAgents(list)
      } catch {
        // Derive from mock
        const unique = new Map<string, string>()
        MOCK_LOGS.forEach((l) => unique.set(l.agent.id, l.agent.name))
        setAgents(Array.from(unique, ([id, name]) => ({ id, name })))
      }
    })()
  }, [])

  // ── Helpers ───────────────────────────────────────────────────────────────
  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "—"
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}m ${s.toString().padStart(2, "0")}s`
  }

  const formatDateTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
      " " +
      d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
  }

  const RatingBadge = ({ rating }: { rating: number | null }) => {
    if (rating === 1)
      return (
        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
          <ThumbsUp className="w-3 h-3 mr-1" /> Good
        </Badge>
      )
    if (rating === -1)
      return (
        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
          <ThumbsDown className="w-3 h-3 mr-1" /> Bad
        </Badge>
      )
    return (
      <Badge variant="outline" className="text-muted-foreground">
        Unrated
      </Badge>
    )
  }

  // ── Detail view ───────────────────────────────────────────────────────────
  const selectedLog = logs.find((l) => l.id === selectedLogId)

  if (selectedLog) {
    return (
      <CallLogDetails
        log={selectedLog}
        onBack={() => setSelectedLogId(null)}
        onUpdated={loadLogs}
      />
    )
  }

  // ── List view ─────────────────────────────────────────────────────────────
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
                <p className="text-muted-foreground">
                  Monitor and review all customer interactions
                </p>
              </div>
              <Button variant="outline">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>

            {/* Filters */}
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="flex flex-wrap items-end gap-4">
                  {/* Agent filter */}
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">Agent</label>
                    <Select value={agentFilter} onValueChange={(v) => { setAgentFilter(v); setPage(1) }}>
                      <SelectTrigger className="w-48">
                        <SelectValue placeholder="All Agents" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Agents</SelectItem>
                        {agents.map((a) => (
                          <SelectItem key={a.id} value={a.id}>
                            {a.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Date range */}
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">From</label>
                    <Input
                      type="date"
                      value={fromDate}
                      onChange={(e) => { setFromDate(e.target.value); setPage(1) }}
                      className="w-40"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground">To</label>
                    <Input
                      type="date"
                      value={toDate}
                      onChange={(e) => { setToDate(e.target.value); setPage(1) }}
                      className="w-40"
                    />
                  </div>

                  {(fromDate || toDate || agentFilter !== "all") && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { setAgentFilter("all"); setFromDate(""); setToDate(""); setPage(1) }}
                    >
                      Clear filters
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Logs table */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Interactions</CardTitle>
                <CardDescription>
                  {loading ? "Loading…" : `${total} interaction${total !== 1 ? "s" : ""} found`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                    Loading call logs…
                  </div>
                ) : logs.length === 0 ? (
                  <div className="text-center py-16 text-muted-foreground">
                    No interactions found matching your criteria.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {logs.map((log) => (
                      <div
                        key={log.id}
                        className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => setSelectedLogId(log.id)}
                      >
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <div className="p-2 bg-muted rounded">
                            <Phone className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-sm">{log.agent.name}</span>
                              {log.flaggedForRetraining && (
                                <Flag className="w-3.5 h-3.5 text-orange-500" />
                              )}
                            </div>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {formatDateTime(log.startedAt)}
                              </span>
                              <span>{formatDuration(log.durationSeconds)}</span>
                            </div>
                          </div>
                        </div>
                        <RatingBadge rating={log.rating} />
                      </div>
                    ))}
                  </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-6 pt-4 border-t">
                    <span className="text-sm text-muted-foreground">
                      Page {page} of {totalPages}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page <= 1}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        <ChevronLeft className="w-4 h-4 mr-1" /> Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        Next <ChevronRight className="w-4 h-4 ml-1" />
                      </Button>
                    </div>
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
