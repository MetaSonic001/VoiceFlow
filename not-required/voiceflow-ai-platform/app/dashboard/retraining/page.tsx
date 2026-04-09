"use client"

import { useState, useEffect } from "react"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { RefreshCw, Check, X, Trash2, Play, MessageSquare, ChevronLeft, ChevronRight } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface RetrainingExample {
  id: string
  tenantId: string
  agentId: string
  callLogId: string
  userQuery: string
  badResponse: string
  idealResponse: string
  status: string
  approvedAt: string | null
  createdAt: string
  agent: { id: string; name: string }
  callLog: { id: string; startedAt: string; rating: number | null }
}

interface Stats {
  pending: number
  approved: number
  rejected: number
  flaggedNotProcessed: number
}

export default function RetrainingPage() {
  const [examples, setExamples] = useState<RetrainingExample[]>([])
  const [stats, setStats] = useState<Stats>({ pending: 0, approved: 0, rejected: 0, flaggedNotProcessed: 0 })
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState("")

  useEffect(() => {
    loadData()
  }, [statusFilter, page])

  async function loadData() {
    setLoading(true)
    try {
      const [examplesRes, statsRes] = await Promise.all([
        apiClient.getRetrainingExamples({
          page,
          limit: 20,
          status: statusFilter === "all" ? undefined : statusFilter,
        }),
        apiClient.getRetrainingStats(),
      ])
      setExamples(examplesRes.examples)
      setTotalPages(examplesRes.pages)
      setStats(statsRes)
    } catch (err) {
      console.error("Error loading retraining data:", err)
    } finally {
      setLoading(false)
    }
  }

  async function handleProcess() {
    setProcessing(true)
    try {
      const result = await apiClient.triggerRetrainingPipeline()
      alert(`Pipeline processed. ${result.examplesCreated} new examples created.`)
      loadData()
    } catch (err) {
      console.error("Error running pipeline:", err)
    } finally {
      setProcessing(false)
    }
  }

  async function handleApprove(id: string) {
    try {
      const payload: { status: "approved"; idealResponse?: string } = { status: "approved" }
      if (editingId === id && editValue.trim()) {
        payload.idealResponse = editValue.trim()
      }
      await apiClient.updateRetrainingExample(id, payload)
      setEditingId(null)
      loadData()
    } catch (err) {
      console.error("Error approving:", err)
    }
  }

  async function handleReject(id: string) {
    try {
      await apiClient.updateRetrainingExample(id, { status: "rejected" })
      loadData()
    } catch (err) {
      console.error("Error rejecting:", err)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this example permanently?")) return
    try {
      await apiClient.deleteRetrainingExample(id)
      loadData()
    } catch (err) {
      console.error("Error deleting:", err)
    }
  }

  function startEdit(example: RetrainingExample) {
    setEditingId(example.id)
    setEditValue(example.idealResponse)
  }

  async function saveEdit(id: string) {
    try {
      await apiClient.updateRetrainingExample(id, { idealResponse: editValue.trim() })
      setEditingId(null)
      loadData()
    } catch (err) {
      console.error("Error saving:", err)
    }
  }

  const statusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <Badge variant="outline" className="text-yellow-600 border-yellow-300">Pending</Badge>
      case "approved":
        return <Badge variant="outline" className="text-green-600 border-green-300">Approved</Badge>
      case "rejected":
        return <Badge variant="outline" className="text-red-600 border-red-300">Rejected</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      <DashboardSidebar />

      <main className="flex-1 ml-64 p-8">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Retraining Queue</h1>
              <p className="text-muted-foreground mt-1">
                Review flagged conversations and approve corrected responses for in-context learning.
              </p>
            </div>
            <Button onClick={handleProcess} disabled={processing} variant="outline">
              <Play className="w-4 h-4 mr-2" />
              {processing ? "Processing..." : "Run Pipeline Now"}
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
                <div className="text-sm text-muted-foreground">Pending Review</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-green-600">{stats.approved}</div>
                <div className="text-sm text-muted-foreground">Approved</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-red-600">{stats.rejected}</div>
                <div className="text-sm text-muted-foreground">Rejected</div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <div className="text-2xl font-bold text-orange-600">{stats.flaggedNotProcessed}</div>
                <div className="text-sm text-muted-foreground">Flagged (Unprocessed)</div>
              </CardContent>
            </Card>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4">
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1) }}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Filter status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={loadData}>
              <RefreshCw className="w-4 h-4 mr-1" /> Refresh
            </Button>
          </div>

          {/* Examples list */}
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">Loading...</div>
          ) : examples.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-lg">No retraining examples yet.</p>
                <p className="text-sm mt-1">
                  Flag bad conversations from the Call Logs page, then run the pipeline.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {examples.map((ex) => (
                <Card key={ex.id} className="overflow-hidden">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {statusBadge(ex.status)}
                        <span className="text-sm text-muted-foreground">
                          Agent: <strong>{ex.agent.name}</strong>
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {new Date(ex.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {ex.status === "pending" && (
                          <>
                            <Button size="sm" variant="outline" className="text-green-600" onClick={() => handleApprove(ex.id)}>
                              <Check className="w-4 h-4 mr-1" /> Approve
                            </Button>
                            <Button size="sm" variant="outline" className="text-red-600" onClick={() => handleReject(ex.id)}>
                              <X className="w-4 h-4 mr-1" /> Reject
                            </Button>
                          </>
                        )}
                        <Button size="sm" variant="ghost" className="text-destructive" onClick={() => handleDelete(ex.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">USER QUERY</div>
                      <div className="bg-muted/50 rounded p-3 text-sm">{ex.userQuery}</div>
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-red-500 mb-1">BAD RESPONSE</div>
                      <div className="bg-red-50 dark:bg-red-950/20 rounded p-3 text-sm">{ex.badResponse}</div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <div className="text-xs font-semibold text-green-600">IDEAL RESPONSE</div>
                        {editingId !== ex.id && (
                          <Button size="sm" variant="ghost" className="text-xs h-6" onClick={() => startEdit(ex)}>
                            Edit
                          </Button>
                        )}
                      </div>
                      {editingId === ex.id ? (
                        <div className="space-y-2">
                          <Textarea
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="min-h-[100px]"
                          />
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => saveEdit(ex.id)}>Save</Button>
                            <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                          </div>
                        </div>
                      ) : (
                        <div className="bg-green-50 dark:bg-green-950/20 rounded p-3 text-sm">{ex.idealResponse}</div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-4 pt-4">
                  <Button
                    variant="outline" size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="outline" size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
