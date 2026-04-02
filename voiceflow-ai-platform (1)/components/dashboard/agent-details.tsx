"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, Phone, MessageSquare, Settings, BarChart3, Play, Pause, Loader2, CheckCircle, Brain } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Agent {
  id: string
  name: string
  role: string
  status: string
  channels: string[]
  phoneNumber: string | null
  totalCalls: number
  totalChats: number
  successRate: number
  avgResponseTime: string
  lastActive: string
  createdAt: string
  llmPreferences?: { model?: string } | null
  tokenLimit?: number | null
  contextWindowStrategy?: string | null
}

interface GroqModel {
  id: string
  name: string
  speed: string
  contextWindow: number
  maxCompletionTokens: number
  description: string
}

interface AgentDetailsProps {
  agent: Agent
  onBack: () => void
}

export function AgentDetails({ agent, onBack }: AgentDetailsProps) {
  const [activeTab, setActiveTab] = useState("overview")

  // LLM settings state
  const [availableModels, setAvailableModels] = useState<GroqModel[]>([])
  const [selectedModel, setSelectedModel] = useState(agent.llmPreferences?.model || 'llama-3.3-70b-versatile')
  const [selectedTokenLimit, setSelectedTokenLimit] = useState(String(agent.tokenLimit || 4096))
  const [selectedStrategy, setSelectedStrategy] = useState(agent.contextWindowStrategy || 'condense')
  const [settingsSaving, setSettingsSaving] = useState(false)
  const [settingsMessage, setSettingsMessage] = useState('')

  useEffect(() => {
    apiClient.getGroqModels()
      .then(data => setAvailableModels(data.models))
      .catch(() => {
        // Fallback if endpoint not reachable
        setAvailableModels([
          { id: 'llama-3.3-70b-versatile', name: 'Meta Llama 3.3 70B', speed: '280 T/sec', contextWindow: 131072, maxCompletionTokens: 32768, description: 'Best quality' },
          { id: 'llama-3.1-8b-instant', name: 'Meta Llama 3.1 8B', speed: '560 T/sec', contextWindow: 131072, maxCompletionTokens: 131072, description: 'Fastest' },
          { id: 'openai/gpt-oss-120b', name: 'OpenAI GPT OSS 120B', speed: '500 T/sec', contextWindow: 131072, maxCompletionTokens: 65536, description: 'Balanced' },
          { id: 'openai/gpt-oss-20b', name: 'OpenAI GPT OSS 20B', speed: '1000 T/sec', contextWindow: 131072, maxCompletionTokens: 65536, description: 'Ultra-fast' },
        ])
      })
  }, [])

  const saveLlmSettings = async () => {
    setSettingsSaving(true)
    setSettingsMessage('')
    try {
      await apiClient.updateAgent(agent.id, {
        llmPreferences: { model: selectedModel },
        tokenLimit: parseInt(selectedTokenLimit, 10),
        contextWindowStrategy: selectedStrategy,
      })
      setSettingsMessage('Settings saved!')
      setTimeout(() => setSettingsMessage(''), 3000)
    } catch {
      setSettingsMessage('Failed to save settings')
      setTimeout(() => setSettingsMessage(''), 3000)
    } finally {
      setSettingsSaving(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800 border-green-200"
      case "paused":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "draft":
        return "bg-gray-100 text-gray-800 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  // Mock conversation data
  const recentConversations = [
    {
      id: "conv-1",
      type: "phone",
      customerPhone: "+1 (555) 987-6543",
      duration: "3m 24s",
      status: "completed",
      timestamp: "2 hours ago",
      summary: "Customer inquiry about product pricing and availability",
    },
    {
      id: "conv-2",
      type: "chat",
      customerName: "Anonymous",
      duration: "1m 45s",
      status: "completed",
      timestamp: "4 hours ago",
      summary: "Support request for password reset assistance",
    },
    {
      id: "conv-3",
      type: "phone",
      customerPhone: "+1 (555) 123-9876",
      duration: "5m 12s",
      status: "escalated",
      timestamp: "6 hours ago",
      summary: "Complex billing issue requiring human intervention",
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Agents
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            <p className="text-muted-foreground">{agent.role}</p>
          </div>
          <Badge className={getStatusColor(agent.status)} variant="outline">
            {agent.status}
          </Badge>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            Edit Agent
          </Button>
          <Button variant={agent.status === "active" ? "secondary" : "default"}>
            {agent.status === "active" ? (
              <>
                <Pause className="w-4 h-4 mr-2" />
                Pause Agent
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Activate Agent
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Calls</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agent.totalCalls.toLocaleString()}</div>
            <p className="text-xs text-green-600">+15% this week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Chats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agent.totalChats.toLocaleString()}</div>
            <p className="text-xs text-green-600">+8% this week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agent.successRate}%</div>
            <p className="text-xs text-green-600">+2% this week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agent.avgResponseTime}</div>
            <p className="text-xs text-green-600">-0.5s this week</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="conversations">Recent Conversations</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Agent Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Communication Channels</h4>
                  <div className="flex space-x-2">
                    {agent.channels.includes("phone") && (
                      <Badge variant="secondary">
                        <Phone className="w-3 h-3 mr-1" />
                        Phone
                      </Badge>
                    )}
                    {agent.channels.includes("chat") && (
                      <Badge variant="secondary">
                        <MessageSquare className="w-3 h-3 mr-1" />
                        Chat
                      </Badge>
                    )}
                  </div>
                </div>
                {agent.phoneNumber && (
                  <div>
                    <h4 className="font-medium mb-1">Phone Number</h4>
                    <p className="text-sm text-muted-foreground">{agent.phoneNumber}</p>
                  </div>
                )}
                <div>
                  <h4 className="font-medium mb-1">Created</h4>
                  <p className="text-sm text-muted-foreground">{agent.createdAt}</p>
                </div>
                <div>
                  <h4 className="font-medium mb-1">Last Active</h4>
                  <p className="text-sm text-muted-foreground">{agent.lastActive}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Knowledge Base</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Documents</span>
                  <Badge variant="outline">3 files</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Website Content</span>
                  <Badge variant="outline">1 site</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">FAQ Entries</span>
                  <Badge variant="outline">24 items</Badge>
                </div>
                <Button variant="outline" size="sm" className="w-full mt-4 bg-transparent">
                  Update Knowledge Base
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="conversations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Conversations</CardTitle>
              <CardDescription>Latest interactions with your AI agent</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentConversations.map((conversation) => (
                  <div
                    key={conversation.id}
                    className="flex items-center justify-between p-4 border border-border rounded-lg"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="p-2 bg-muted rounded">
                        {conversation.type === "phone" ? (
                          <Phone className="w-4 h-4" />
                        ) : (
                          <MessageSquare className="w-4 h-4" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium">
                          {conversation.type === "phone" ? conversation.customerPhone : "Website Chat"}
                        </p>
                        <p className="text-sm text-muted-foreground">{conversation.summary}</p>
                        <p className="text-xs text-muted-foreground">{conversation.timestamp}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge variant={conversation.status === "completed" ? "secondary" : "destructive"}>
                        {conversation.status}
                      </Badge>
                      <p className="text-sm text-muted-foreground mt-1">{conversation.duration}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5" />
                <span>Analytics Dashboard</span>
              </CardTitle>
              <CardDescription>Detailed performance metrics and insights</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <BarChart3 className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">Analytics dashboard will be implemented in the next phase</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Brain className="w-5 h-5" />
                <span>LLM &amp; Inference Settings</span>
              </CardTitle>
              <CardDescription>Choose which Groq model this agent uses and configure token limits.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {settingsMessage && (
                <div className={`flex items-center gap-2 p-3 rounded-lg ${settingsMessage.includes('saved') ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-800'}`}>
                  <CheckCircle className="w-4 h-4" />
                  <span className="text-sm">{settingsMessage}</span>
                </div>
              )}

              {/* Model selection */}
              <div className="space-y-3">
                <Label>Groq Model</Label>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableModels.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{m.name}</span>
                          <span className="text-xs text-muted-foreground">({m.speed})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {availableModels.find(m => m.id === selectedModel) && (
                  <p className="text-xs text-muted-foreground">
                    {availableModels.find(m => m.id === selectedModel)!.description}
                    {' — '}Context: {(availableModels.find(m => m.id === selectedModel)!.contextWindow / 1024).toFixed(0)}K tokens
                  </p>
                )}
              </div>

              <Separator />

              {/* Token limit */}
              <div className="space-y-3">
                <Label>Max Token Limit</Label>
                <Select value={selectedTokenLimit} onValueChange={setSelectedTokenLimit}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2048">2,048 tokens (fast, short answers)</SelectItem>
                    <SelectItem value="4096">4,096 tokens (default)</SelectItem>
                    <SelectItem value="8192">8,192 tokens (detailed answers)</SelectItem>
                    <SelectItem value="16384">16,384 tokens (long-form)</SelectItem>
                    <SelectItem value="32768">32,768 tokens (maximum)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Controls the maximum response length. Higher limits use more API credits.
                </p>
              </div>

              <Separator />

              {/* Context window strategy */}
              <div className="space-y-3">
                <Label>Context Window Strategy</Label>
                <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="condense">Condense (rank &amp; trim to fit)</SelectItem>
                    <SelectItem value="truncate">Truncate (cut off oldest context)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  How retrieved knowledge chunks are managed when they exceed the token limit.
                </p>
              </div>

              <div className="pt-4">
                <Button onClick={saveLlmSettings} disabled={settingsSaving}>
                  {settingsSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Save Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
