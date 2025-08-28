"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowLeft, Phone, MessageSquare, Settings, BarChart3, Play, Pause } from "lucide-react"

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
}

interface AgentDetailsProps {
  agent: Agent
  onBack: () => void
}

export function AgentDetails({ agent, onBack }: AgentDetailsProps) {
  const [activeTab, setActiveTab] = useState("overview")

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
              <CardTitle>Agent Settings</CardTitle>
              <CardDescription>Configure your agent's behavior and preferences</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Settings className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">Settings panel will be implemented in the next phase</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
