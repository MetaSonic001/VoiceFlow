"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import {
  ArrowLeft,
  Phone,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Flag,
  Loader2,
  CheckCircle,
  Bot,
  User,
} from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { cn } from "@/lib/utils"

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

interface TranscriptMessage {
  speaker: "agent" | "customer"
  message: string
  timestamp?: string
}

interface CallLogDetailsProps {
  log: CallLogEntry
  onBack: () => void
  onUpdated?: () => void
}

export function CallLogDetails({ log, onBack, onUpdated }: CallLogDetailsProps) {
  const [rating, setRating] = useState<1 | -1 | null>(log.rating as 1 | -1 | null)
  const [notes, setNotes] = useState(log.ratingNotes || "")
  const [showNotes, setShowNotes] = useState(false)
  const [ratingSubmitting, setRatingSubmitting] = useState(false)
  const [ratingDone, setRatingDone] = useState(false)

  const [flagged, setFlagged] = useState(log.flaggedForRetraining)
  const [flagging, setFlagging] = useState(false)

  // Parse transcript — stored as JSON array or plain text
  const messages: TranscriptMessage[] = (() => {
    try {
      const parsed = JSON.parse(log.transcript)
      if (Array.isArray(parsed)) {
        return parsed.map((m: any) => {
          // Support both { speaker, message } and { role, content } formats
          const speaker = m.speaker ?? (m.role === 'user' || m.role === 'customer' ? 'customer' : 'agent')
          const message = m.message ?? m.content ?? ''
          return { speaker, message, timestamp: m.timestamp } as TranscriptMessage
        })
      }
    } catch { /* not JSON */ }
    // Fallback: treat whole transcript as a single agent message
    return [{ speaker: "agent" as const, message: log.transcript }]
  })()

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "—"
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}m ${s.toString().padStart(2, "0")}s`
  }

  const formatDateTime = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })

  const handleRatingClick = (value: 1 | -1) => {
    setRating(value)
    setShowNotes(true)
  }

  const handleSubmitRating = async () => {
    if (!rating) return
    setRatingSubmitting(true)
    try {
      await apiClient.rateCallLog(log.id, rating, notes || undefined)
      setRatingDone(true)
      onUpdated?.()
    } catch {
      // silent — UI already shows the selection
    } finally {
      setRatingSubmitting(false)
    }
  }

  const handleFlag = async () => {
    setFlagging(true)
    try {
      await apiClient.flagCallLogForRetraining(log.id)
      setFlagged(true)
      onUpdated?.()
    } catch {
      // silent
    } finally {
      setFlagging(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
              <Button variant="ghost" onClick={onBack}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Logs
              </Button>
              <div className="flex-1">
                <h1 className="text-2xl font-bold">Interaction Details</h1>
                <p className="text-sm text-muted-foreground">ID: {log.id}</p>
              </div>
              {flagged && (
                <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                  <Flag className="w-3 h-3 mr-1" />
                  Flagged for retraining
                </Badge>
              )}
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
              {/* Main — Transcript */}
              <div className="lg:col-span-2 space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Conversation Transcript</CardTitle>
                    <CardDescription>
                      {messages.length} message{messages.length !== 1 ? "s" : ""}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                      {messages.map((msg, i) => (
                        <div
                          key={i}
                          className={cn(
                            "flex gap-2",
                            msg.speaker === "customer" ? "justify-end" : "justify-start"
                          )}
                        >
                          {msg.speaker === "agent" && (
                            <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                              <Bot className="w-3.5 h-3.5 text-primary" />
                            </div>
                          )}
                          <div
                            className={cn(
                              "max-w-[70%] p-3 rounded-2xl text-sm",
                              msg.speaker === "customer"
                                ? "bg-primary text-primary-foreground rounded-br-md"
                                : "bg-muted rounded-bl-md"
                            )}
                          >
                            {msg.timestamp && (
                              <span className="text-[10px] opacity-60 block mb-1">{msg.timestamp}</span>
                            )}
                            {msg.message}
                          </div>
                          {msg.speaker === "customer" && (
                            <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center flex-shrink-0 mt-1">
                              <User className="w-3.5 h-3.5 text-muted-foreground" />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Rating widget */}
                <Card>
                  <CardHeader>
                    <CardTitle>Rate this conversation</CardTitle>
                    <CardDescription>Help improve your agent by rating call quality</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {ratingDone ? (
                      <div className="flex items-center gap-2 text-green-600">
                        <CheckCircle className="w-4 h-4" />
                        Rating submitted — thank you!
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className="flex gap-3">
                          <Button
                            variant={rating === 1 ? "default" : "outline"}
                            className={cn(
                              "gap-2",
                              rating === 1 && "bg-green-600 hover:bg-green-700"
                            )}
                            onClick={() => handleRatingClick(1)}
                          >
                            <ThumbsUp className="w-4 h-4" /> Good
                          </Button>
                          <Button
                            variant={rating === -1 ? "default" : "outline"}
                            className={cn(
                              "gap-2",
                              rating === -1 && "bg-red-600 hover:bg-red-700"
                            )}
                            onClick={() => handleRatingClick(-1)}
                          >
                            <ThumbsDown className="w-4 h-4" /> Bad
                          </Button>
                        </div>

                        {showNotes && (
                          <>
                            <Textarea
                              placeholder="Optional notes — what went well or wrong?"
                              value={notes}
                              onChange={(e) => setNotes(e.target.value)}
                              rows={3}
                            />
                            <Button onClick={handleSubmitRating} disabled={ratingSubmitting || !rating}>
                              {ratingSubmitting ? (
                                <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Submitting…</>
                              ) : (
                                "Submit rating"
                              )}
                            </Button>
                          </>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Sidebar — metadata + actions */}
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Call Metadata</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-muted-foreground" />
                      <span className="font-medium">{log.agent.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span>{formatDateTime(log.startedAt)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Duration: </span>
                      <span className="font-medium">{formatDuration(log.durationSeconds)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Rating: </span>
                      {rating === 1 ? (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          <ThumbsUp className="w-3 h-3 mr-1" /> Good
                        </Badge>
                      ) : rating === -1 ? (
                        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                          <ThumbsDown className="w-3 h-3 mr-1" /> Bad
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">Unrated</span>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Actions</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full gap-2"
                      onClick={handleFlag}
                      disabled={flagged || flagging}
                    >
                      {flagging ? (
                        <><Loader2 className="w-4 h-4 animate-spin" /> Flagging…</>
                      ) : flagged ? (
                        <><Flag className="w-4 h-4 text-orange-500" /> Flagged for retraining</>
                      ) : (
                        <><Flag className="w-4 h-4" /> Flag for retraining</>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
