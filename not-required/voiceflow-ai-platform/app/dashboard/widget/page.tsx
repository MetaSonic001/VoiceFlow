"use client"

import { useState, useEffect } from "react"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Copy, Check, Globe, Phone, Code2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Agent {
  id: string
  name: string
  status: string
  phoneNumber?: string | null
}

export default function WidgetPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [showApiDocs, setShowApiDocs] = useState<string | null>(null)

  const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  useEffect(() => {
    loadAgents()
  }, [])

  async function loadAgents() {
    try {
      const res = await apiClient.getAgents()
      setAgents(res.agents)
    } catch (err) {
      console.error("Error loading agents:", err)
    } finally {
      setLoading(false)
    }
  }

  function getEmbedCode(agentId: string) {
    return `<script src="${backendUrl}/api/widget/${agentId}/embed.js" async></script>`
  }

  function copyToClipboard(agentId: string) {
    navigator.clipboard.writeText(getEmbedCode(agentId))
    setCopiedId(agentId)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="flex min-h-screen bg-background">
      <DashboardSidebar />

      <main className="flex-1 ml-64 p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Embeddable Call Widget</h1>
            <p className="text-muted-foreground mt-1">
              Add a voice AI assistant to any website with a single script tag.
              Visitors can talk to your agents directly from their browser — no phone number needed.
            </p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>How it works</CardTitle>
              <CardDescription>
                The widget creates a floating call button on your website. When a visitor clicks it,
                it opens a browser-based voice call to your AI agent using WebRTC.
                Calls go through the same RAG knowledge base as phone calls.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex items-start gap-3">
                <Badge variant="outline" className="shrink-0 mt-0.5">1</Badge>
                <span>Copy the embed snippet for your agent below</span>
              </div>
              <div className="flex items-start gap-3">
                <Badge variant="outline" className="shrink-0 mt-0.5">2</Badge>
                <span>Paste it into your website HTML before the <code className="bg-muted px-1 rounded">&lt;/body&gt;</code> tag</span>
              </div>
              <div className="flex items-start gap-3">
                <Badge variant="outline" className="shrink-0 mt-0.5">3</Badge>
                <span>A call button appears in the bottom-right corner — visitors can start talking to your agent immediately</span>
              </div>
            </CardContent>
          </Card>

          {loading ? (
            <div className="text-center py-12 text-muted-foreground">Loading agents...</div>
          ) : agents.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                No agents found. Create an agent first to get a widget embed code.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {agents.map((agent) => (
                <Card key={agent.id}>
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center">
                          <Globe className="w-5 h-5 text-indigo-600" />
                        </div>
                        <div>
                          <div className="font-semibold">{agent.name}</div>
                          <div className="text-sm text-muted-foreground flex items-center gap-2">
                            {agent.phoneNumber ? (
                              <>
                                <Phone className="w-3 h-3" /> {agent.phoneNumber}
                                <span className="text-xs">+ WebRTC</span>
                              </>
                            ) : (
                              <span>WebRTC only (no phone number)</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <Badge variant={agent.status === "active" ? "default" : "secondary"}>
                        {agent.status}
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-muted-foreground">EMBED CODE</div>
                      <div className="relative">
                        <pre className="bg-muted rounded-lg p-4 text-xs overflow-x-auto font-mono">
                          {getEmbedCode(agent.id)}
                        </pre>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="absolute top-2 right-2"
                          onClick={() => copyToClipboard(agent.id)}
                        >
                          {copiedId === agent.id ? (
                            <Check className="w-4 h-4 text-green-500" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </div>

                    <div className="mt-4 border-t pt-4">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowApiDocs(showApiDocs === agent.id ? null : agent.id)}
                        className="gap-2"
                      >
                        <Code2 className="w-4 h-4" />
                        {showApiDocs === agent.id ? "Hide" : "Show"} REST API
                      </Button>

                      {showApiDocs === agent.id && (
                        <div className="mt-4 space-y-4">
                          <div className="text-xs font-semibold text-muted-foreground">REST API — INTEGRATE IN YOUR OWN APP</div>
                          <p className="text-xs text-muted-foreground">
                            Use these endpoints to integrate the AI voice agent into your own frontend or backend.
                            No authentication needed — the agentId is the public key.
                          </p>

                          <div className="space-y-3 text-xs font-mono">
                            <div className="bg-muted rounded-lg p-4 space-y-2">
                              <div className="font-semibold text-foreground">1. Create a session</div>
                              <pre className="text-muted-foreground whitespace-pre-wrap">{`POST ${backendUrl}/api/widget/${agent.id}/sessions

Response: { "sessionId": "api_xxx", "agentId": "${agent.id}", "agentName": "${agent.name}", "wsEndpoint": "..." }`}</pre>
                            </div>

                            <div className="bg-muted rounded-lg p-4 space-y-2">
                              <div className="font-semibold text-foreground">2. Send a message</div>
                              <pre className="text-muted-foreground whitespace-pre-wrap">{`POST ${backendUrl}/api/widget/${agent.id}/sessions/{sessionId}/message
Content-Type: application/json
{ "text": "What are your business hours?" }

Response: { "response": "Our business hours are...", "sessionId": "..." }`}</pre>
                            </div>

                            <div className="bg-muted rounded-lg p-4 space-y-2">
                              <div className="font-semibold text-foreground">3. Get session transcript</div>
                              <pre className="text-muted-foreground whitespace-pre-wrap">{`GET ${backendUrl}/api/widget/${agent.id}/sessions/{sessionId}

Response: { "messages": [{ "role": "user", "content": "..." }, ...] }`}</pre>
                            </div>

                            <div className="bg-muted rounded-lg p-4 space-y-2">
                              <div className="font-semibold text-foreground">4. End session</div>
                              <pre className="text-muted-foreground whitespace-pre-wrap">{`DELETE ${backendUrl}/api/widget/${agent.id}/sessions/{sessionId}

Response: { "success": true }`}</pre>
                            </div>
                          </div>

                          <p className="text-xs text-muted-foreground">
                            For real-time voice, connect to the WebSocket endpoint returned in step 1
                            using Socket.IO with <code className="bg-muted px-1 rounded">path: &quot;/ws&quot;</code> and query params 
                            <code className="bg-muted px-1 rounded">{`{ agentId: "${agent.id}", tenantId: "..." }`}</code>.
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
