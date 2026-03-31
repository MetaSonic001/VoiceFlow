"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Bot, MessageSquare, FileText, Sparkles, Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface UsageSummary {
  agents: number
  callLogs: number
  documents: number
}

export default function BillingPage() {
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.getUsageStats()
      .then((data) => setUsage(data as UsageSummary))
      .catch(() => setUsage(null))
      .finally(() => setLoading(false))
  }, [])

  const stats = [
    {
      label: "AI Agents created",
      value: usage?.agents ?? 0,
      icon: <Bot className="w-6 h-6 text-primary" />,
      description: "Active agents in your workspace",
    },
    {
      label: "Conversations logged",
      value: usage?.callLogs ?? 0,
      icon: <MessageSquare className="w-6 h-6 text-primary" />,
      description: "Total RAG queries recorded",
    },
    {
      label: "Documents indexed",
      value: usage?.documents ?? 0,
      icon: <FileText className="w-6 h-6 text-primary" />,
      description: "Files in your knowledge base",
    },
  ]

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Billing &amp; Usage</h1>
            <p className="text-muted-foreground mt-1">Your current platform usage at a glance.</p>
          </div>
          <Badge variant="secondary" className="text-sm px-3 py-1 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            Free Beta
          </Badge>
        </div>

        {/* Beta notice */}
        <Card className="mb-8 border-primary/30 bg-primary/5">
          <CardContent className="pt-5 pb-5">
            <p className="text-sm leading-relaxed">
              VoiceFlow is currently in <strong>free beta</strong>. All features are available at no cost. Billing and subscription management will be introduced before the public launch — we will notify you well in advance.
            </p>
          </CardContent>
        </Card>

        {/* Real usage counters */}
        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          {stats.map((stat) => (
            <Card key={stat.label}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-3">
                  {stat.icon}
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  ) : (
                    <span className="text-3xl font-bold">{stat.value.toLocaleString()}</span>
                  )}
                </div>
                <p className="font-medium text-sm">{stat.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{stat.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Coming soon section */}
        <Card className="border-dashed">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Subscription &amp; Invoices</CardTitle>
            <CardDescription>Coming before public launch.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Tiered plans (Starter, Professional, Enterprise)</li>
              <li>Usage-based billing with monthly invoices</li>
              <li>Downloadable PDF invoices</li>
              <li>Overage notifications and spending limits</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
