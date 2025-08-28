"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Phone, MessageCircle, User, Bot, Eye, Volume2 } from "lucide-react"

interface LiveConversation {
  id: string
  type: "phone" | "chat"
  agentName: string
  customerInfo: string
  duration: string
  status: "active" | "on_hold" | "transferring"
  lastMessage: string
  sentiment: "positive" | "neutral" | "negative"
  transcript: Array<{
    speaker: "agent" | "customer"
    message: string
    timestamp: string
  }>
}

const mockConversations: LiveConversation[] = [
  {
    id: "conv-1",
    type: "phone",
    agentName: "Customer Support Assistant",
    customerInfo: "+1 (555) 987-6543",
    duration: "3:45",
    status: "active",
    lastMessage: "Let me check your account details right away.",
    sentiment: "positive",
    transcript: [
      { speaker: "agent", message: "Hello! Thank you for calling. How can I help you today?", timestamp: "3:45 ago" },
      {
        speaker: "customer",
        message: "Hi, I'm having trouble with my recent order. It hasn't arrived yet.",
        timestamp: "3:30 ago",
      },
      {
        speaker: "agent",
        message: "I'm sorry to hear that. Let me check your account details right away.",
        timestamp: "just now",
      },
    ],
  },
  {
    id: "conv-2",
    type: "chat",
    agentName: "Sales Qualifier",
    customerInfo: "john.doe@business.com",
    duration: "7:22",
    status: "active",
    lastMessage: "That sounds like a perfect fit for our enterprise plan.",
    sentiment: "positive",
    transcript: [
      {
        speaker: "customer",
        message: "I'm interested in your AI agent solution for our customer service team.",
        timestamp: "7:22 ago",
      },
      {
        speaker: "agent",
        message: "Great! I'd be happy to help. How many customer service representatives do you currently have?",
        timestamp: "7:10 ago",
      },
      {
        speaker: "customer",
        message: "We have about 25 agents handling around 500 calls per day.",
        timestamp: "6:45 ago",
      },
      { speaker: "agent", message: "That sounds like a perfect fit for our enterprise plan.", timestamp: "just now" },
    ],
  },
  {
    id: "conv-3",
    type: "phone",
    agentName: "HR Assistant",
    customerInfo: "employee@company.com",
    duration: "1:15",
    status: "on_hold",
    lastMessage: "Please hold while I verify your employment details.",
    sentiment: "neutral",
    transcript: [
      { speaker: "agent", message: "Hello, this is the HR assistant. How can I help you?", timestamp: "1:15 ago" },
      { speaker: "customer", message: "I need to update my emergency contact information.", timestamp: "1:00 ago" },
      { speaker: "agent", message: "Please hold while I verify your employment details.", timestamp: "45s ago" },
    ],
  },
]

export function LiveConversations() {
  const [conversations, setConversations] = useState<LiveConversation[]>(mockConversations)
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null)

  useEffect(() => {
    const interval = setInterval(() => {
      setConversations((prev) =>
        prev.map((conv) => {
          // Randomly update conversation duration and add new messages
          if (Math.random() > 0.7 && conv.status === "active") {
            const newMessage = {
              speaker: Math.random() > 0.5 ? ("agent" as const) : ("customer" as const),
              message:
                conv.type === "phone"
                  ? "I understand your concern. Let me help you with that."
                  : "Thank you for the information. I'll process that for you.",
              timestamp: "just now",
            }

            return {
              ...conv,
              transcript: [...conv.transcript, newMessage],
              lastMessage: newMessage.message,
              duration: updateDuration(conv.duration),
            }
          }

          return {
            ...conv,
            duration: conv.status === "active" ? updateDuration(conv.duration) : conv.duration,
          }
        }),
      )
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const updateDuration = (duration: string): string => {
    const [minutes, seconds] = duration.split(":").map(Number)
    const totalSeconds = minutes * 60 + seconds + 10
    const newMinutes = Math.floor(totalSeconds / 60)
    const newSeconds = totalSeconds % 60
    return `${newMinutes}:${newSeconds.toString().padStart(2, "0")}`
  }

  const getSentimentColor = (sentiment: LiveConversation["sentiment"]) => {
    switch (sentiment) {
      case "positive":
        return "text-green-600"
      case "negative":
        return "text-red-600"
      default:
        return "text-yellow-600"
    }
  }

  const getStatusBadge = (status: LiveConversation["status"]) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500">Active</Badge>
      case "on_hold":
        return <Badge variant="secondary">On Hold</Badge>
      case "transferring":
        return <Badge variant="outline">Transferring</Badge>
    }
  }

  const selectedConv = conversations.find((c) => c.id === selectedConversation)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5" />
            Live Conversations ({conversations.length})
          </span>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              {conversations.filter((c) => c.status === "active").length} Active
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="list" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="list">Conversation List</TabsTrigger>
            <TabsTrigger value="monitor">Live Monitor</TabsTrigger>
          </TabsList>

          <TabsContent value="list" className="space-y-4">
            <ScrollArea className="h-80">
              <div className="space-y-3">
                {conversations.map((conversation) => (
                  <div key={conversation.id} className="p-4 border rounded-lg bg-card/50">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-full bg-primary/10">
                          {conversation.type === "phone" ? (
                            <Phone className="w-4 h-4" />
                          ) : (
                            <MessageCircle className="w-4 h-4" />
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-sm">{conversation.agentName}</span>
                            {getStatusBadge(conversation.status)}
                          </div>
                          <div className="text-xs text-muted-foreground mb-2">
                            {conversation.customerInfo} • {conversation.duration}
                          </div>
                          <div className="text-sm text-muted-foreground">"{conversation.lastMessage}"</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className={`text-xs font-medium ${getSentimentColor(conversation.sentiment)}`}>
                          {conversation.sentiment}
                        </div>
                        <Button size="sm" variant="outline" onClick={() => setSelectedConversation(conversation.id)}>
                          <Eye className="w-3 h-3 mr-1" />
                          Monitor
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="monitor" className="space-y-4">
            {selectedConv ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                  <div>
                    <div className="font-medium">{selectedConv.agentName}</div>
                    <div className="text-sm text-muted-foreground">
                      {selectedConv.customerInfo} • {selectedConv.duration}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(selectedConv.status)}
                    {selectedConv.type === "phone" && (
                      <Button size="sm" variant="outline">
                        <Volume2 className="w-3 h-3 mr-1" />
                        Listen
                      </Button>
                    )}
                  </div>
                </div>

                <ScrollArea className="h-60 border rounded-lg p-4">
                  <div className="space-y-3">
                    {selectedConv.transcript.map((message, index) => (
                      <div
                        key={index}
                        className={`flex gap-3 ${message.speaker === "agent" ? "justify-start" : "justify-end"}`}
                      >
                        <div
                          className={`max-w-[80%] p-3 rounded-lg ${
                            message.speaker === "agent"
                              ? "bg-blue-50 border border-blue-200"
                              : "bg-gray-50 border border-gray-200"
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            {message.speaker === "agent" ? (
                              <Bot className="w-3 h-3 text-blue-600" />
                            ) : (
                              <User className="w-3 h-3 text-gray-600" />
                            )}
                            <span className="text-xs font-medium capitalize">{message.speaker}</span>
                            <span className="text-xs text-muted-foreground">{message.timestamp}</span>
                          </div>
                          <div className="text-sm">{message.message}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">Select a conversation to monitor</div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
