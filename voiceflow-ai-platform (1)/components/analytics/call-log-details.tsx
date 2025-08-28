"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { ArrowLeft, Phone, MessageSquare, Clock, User, Tag, ThumbsUp, ThumbsDown } from "lucide-react"

interface CallLog {
  id: string
  type: string
  customerInfo: string
  agentName: string
  startTime: string
  duration: string
  status: string
  resolution: string
  summary: string
  sentiment: string
  tags: string[]
}

interface CallLogDetailsProps {
  log: CallLog
  onBack: () => void
}

export function CallLogDetails({ log, onBack }: CallLogDetailsProps) {
  // Mock conversation transcript
  const transcript = [
    {
      speaker: "agent",
      message: "Hello! Thank you for contacting us. How can I help you today?",
      timestamp: "14:30:25",
    },
    {
      speaker: "customer",
      message: "Hi, I'm interested in your premium plan. Can you tell me about the pricing?",
      timestamp: "14:30:32",
    },
    {
      speaker: "agent",
      message:
        "I'd be happy to help you with information about our premium plan. Our premium plan is currently $29.99 per month and includes unlimited calls, advanced analytics, and priority support.",
      timestamp: "14:30:45",
    },
    {
      speaker: "customer",
      message: "That sounds good. Are there any current promotions or discounts available?",
      timestamp: "14:31:12",
    },
    {
      speaker: "agent",
      message:
        "Yes! We're currently offering a 20% discount for the first 3 months for new customers. That would bring your first 3 months to $23.99 each.",
      timestamp: "14:31:25",
    },
    { speaker: "customer", message: "Perfect! How do I sign up for that?", timestamp: "14:31:45" },
    {
      speaker: "agent",
      message:
        "I can help you get started right away. Would you like me to transfer you to our sales team to complete the signup process?",
      timestamp: "14:31:52",
    },
    { speaker: "customer", message: "Yes, that would be great. Thank you for your help!", timestamp: "14:32:05" },
    { speaker: "agent", message: "You're welcome! I'm transferring you now. Have a great day!", timestamp: "14:32:12" },
  ]

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

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-4">
                <Button variant="ghost" onClick={onBack}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Logs
                </Button>
                <div>
                  <h1 className="text-2xl font-bold">Interaction Details</h1>
                  <p className="text-muted-foreground">ID: {log.id}</p>
                </div>
              </div>
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
              {/* Main Content */}
              <div className="lg:col-span-2 space-y-6">
                {/* Conversation Transcript */}
                <Card>
                  <CardHeader>
                    <CardTitle>Conversation Transcript</CardTitle>
                    <CardDescription>Full conversation between customer and AI agent</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4 max-h-96 overflow-y-auto">
                      {transcript.map((message, index) => (
                        <div
                          key={index}
                          className={`flex ${message.speaker === "customer" ? "justify-end" : "justify-start"}`}
                        >
                          <div
                            className={`max-w-xs lg:max-w-md p-3 rounded-lg ${
                              message.speaker === "customer"
                                ? "bg-accent text-accent-foreground"
                                : "bg-muted text-muted-foreground"
                            }`}
                          >
                            <div className="flex items-center space-x-2 mb-1">
                              <span className="text-xs font-medium capitalize">{message.speaker}</span>
                              <span className="text-xs opacity-70">{message.timestamp}</span>
                            </div>
                            <p className="text-sm">{message.message}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Summary & Analysis */}
                <Card>
                  <CardHeader>
                    <CardTitle>AI Analysis</CardTitle>
                    <CardDescription>Automated summary and insights</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">Summary</h4>
                      <p className="text-sm text-muted-foreground">{log.summary}</p>
                    </div>
                    <Separator />
                    <div>
                      <h4 className="font-medium mb-2">Key Topics</h4>
                      <div className="flex flex-wrap gap-2">
                        {log.tags.map((tag) => (
                          <Badge key={tag} variant="secondary">
                            <Tag className="w-3 h-3 mr-1" />
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Separator />
                    <div>
                      <h4 className="font-medium mb-2">Customer Sentiment</h4>
                      <div className="flex items-center space-x-2">
                        {log.sentiment === "positive" ? (
                          <ThumbsUp className="w-4 h-4 text-green-600" />
                        ) : log.sentiment === "negative" ? (
                          <ThumbsDown className="w-4 h-4 text-red-600" />
                        ) : (
                          <div className="w-4 h-4 bg-gray-400 rounded-full" />
                        )}
                        <span className={`font-medium capitalize ${getSentimentColor(log.sentiment)}`}>
                          {log.sentiment}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                {/* Interaction Info */}
                <Card>
                  <CardHeader>
                    <CardTitle>Interaction Info</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center space-x-2">
                      {log.type === "phone" ? (
                        <Phone className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <MessageSquare className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="text-sm font-medium capitalize">{log.type} Call</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <User className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{log.customerInfo}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{log.startTime}</span>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Duration: </span>
                      <span className="text-sm font-medium">{log.duration}</span>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Status: </span>
                      <Badge className={getStatusColor(log.status)} variant="outline">
                        {log.status}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* Agent Info */}
                <Card>
                  <CardHeader>
                    <CardTitle>Agent Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div>
                      <span className="text-sm text-muted-foreground">Agent: </span>
                      <span className="text-sm font-medium">{log.agentName}</span>
                    </div>
                    <div>
                      <span className="text-sm text-muted-foreground">Resolution: </span>
                      <span className="text-sm font-medium capitalize">{log.resolution}</span>
                    </div>
                  </CardContent>
                </Card>

                {/* Actions */}
                <Card>
                  <CardHeader>
                    <CardTitle>Actions</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button variant="outline" size="sm" className="w-full bg-transparent">
                      Export Transcript
                    </Button>
                    <Button variant="outline" size="sm" className="w-full bg-transparent">
                      Flag for Review
                    </Button>
                    <Button variant="outline" size="sm" className="w-full bg-transparent">
                      Add to Training
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
