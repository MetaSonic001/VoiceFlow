"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Phone, MessageSquare, Mail, MoreVertical, Play, Pause, Settings, Trash2 } from "lucide-react"

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

interface AgentCardProps {
  agent: Agent
  onSelect: () => void
}

export function AgentCard({ agent, onSelect }: AgentCardProps) {
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

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case "phone":
        return <Phone className="w-4 h-4" />
      case "chat":
        return <MessageSquare className="w-4 h-4" />
      case "whatsapp":
        return <MessageSquare className="w-4 h-4" />
      case "email":
        return <Mail className="w-4 h-4" />
      default:
        return null
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={onSelect}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg">{agent.name}</CardTitle>
            <CardDescription className="mt-1">{agent.role}</CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <Badge className={getStatusColor(agent.status)} variant="outline">
              {agent.status}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="sm">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem>
                  <Settings className="w-4 h-4 mr-2" />
                  Edit Agent
                </DropdownMenuItem>
                <DropdownMenuItem>
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
                </DropdownMenuItem>
                <DropdownMenuItem className="text-destructive">
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Agent
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Channels */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-muted-foreground">Channels:</span>
          <div className="flex space-x-1">
            {agent.channels.map((channel) => (
              <div key={channel} className="p-1 bg-muted rounded">
                {getChannelIcon(channel)}
              </div>
            ))}
          </div>
        </div>

        {/* Phone Number */}
        {agent.phoneNumber && (
          <div className="text-sm">
            <span className="text-muted-foreground">Phone:</span> {agent.phoneNumber}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="font-medium">{(agent.totalCalls + agent.totalChats).toLocaleString()}</div>
            <div className="text-muted-foreground">Total Interactions</div>
          </div>
          <div>
            <div className="font-medium">{agent.successRate}%</div>
            <div className="text-muted-foreground">Success Rate</div>
          </div>
        </div>

        {/* Last Active */}
        <div className="text-xs text-muted-foreground">Last active: {agent.lastActive}</div>
      </CardContent>
    </Card>
  )
}
