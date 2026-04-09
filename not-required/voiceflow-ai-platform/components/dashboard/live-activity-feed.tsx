"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Phone, MessageCircle, UserCheck, AlertTriangle, Clock } from "lucide-react"

interface ActivityItem {
  id: string
  type: "call_started" | "call_ended" | "chat_started" | "chat_ended" | "agent_activated" | "escalation"
  agentName: string
  customerInfo: string
  timestamp: string
  status: "success" | "warning" | "error" | "info"
  details?: string
}

const mockActivities: ActivityItem[] = [
  {
    id: "1",
    type: "call_started",
    agentName: "Customer Support Assistant",
    customerInfo: "+1 (555) 987-6543",
    timestamp: "2 seconds ago",
    status: "info",
    details: "Incoming call about billing inquiry",
  },
  {
    id: "2",
    type: "chat_ended",
    agentName: "Sales Qualifier",
    customerInfo: "john.doe@email.com",
    timestamp: "1 minute ago",
    status: "success",
    details: "Lead qualified successfully",
  },
  {
    id: "3",
    type: "escalation",
    agentName: "Customer Support Assistant",
    customerInfo: "+1 (555) 123-4567",
    timestamp: "3 minutes ago",
    status: "warning",
    details: "Complex technical issue escalated to human agent",
  },
  {
    id: "4",
    type: "call_ended",
    agentName: "HR Assistant",
    customerInfo: "employee@company.com",
    timestamp: "5 minutes ago",
    status: "success",
    details: "PTO request processed",
  },
  {
    id: "5",
    type: "chat_started",
    agentName: "Sales Qualifier",
    customerInfo: "prospect@business.com",
    timestamp: "7 minutes ago",
    status: "info",
    details: "Product demo inquiry",
  },
]

export function LiveActivityFeed() {
  const [activities, setActivities] = useState<ActivityItem[]>(mockActivities)

  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate new activity every 10-30 seconds
      if (Math.random() > 0.7) {
        const newActivity: ActivityItem = {
          id: Date.now().toString(),
          type: ["call_started", "chat_started", "call_ended", "chat_ended"][Math.floor(Math.random() * 4)] as any,
          agentName: ["Customer Support Assistant", "Sales Qualifier", "HR Assistant"][Math.floor(Math.random() * 3)],
          customerInfo: `+1 (555) ${Math.floor(Math.random() * 900 + 100)}-${Math.floor(Math.random() * 9000 + 1000)}`,
          timestamp: "just now",
          status: ["success", "info", "warning"][Math.floor(Math.random() * 3)] as any,
          details: "New interaction started",
        }

        setActivities((prev) => [newActivity, ...prev.slice(0, 9)]) // Keep only 10 most recent
      }
    }, 15000)

    return () => clearInterval(interval)
  }, [])

  const getIcon = (type: ActivityItem["type"]) => {
    switch (type) {
      case "call_started":
      case "call_ended":
        return <Phone className="w-4 h-4" />
      case "chat_started":
      case "chat_ended":
        return <MessageCircle className="w-4 h-4" />
      case "agent_activated":
        return <UserCheck className="w-4 h-4" />
      case "escalation":
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <Clock className="w-4 h-4" />
    }
  }

  const getStatusColor = (status: ActivityItem["status"]) => {
    switch (status) {
      case "success":
        return "bg-green-500"
      case "warning":
        return "bg-yellow-500"
      case "error":
        return "bg-red-500"
      default:
        return "bg-blue-500"
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          Live Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-80">
          <div className="space-y-4">
            {activities.map((activity) => (
              <div key={activity.id} className="flex items-start gap-3 p-3 rounded-lg border bg-card/50">
                <div className={`p-2 rounded-full ${getStatusColor(activity.status)} text-white`}>
                  {getIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium truncate">{activity.agentName}</p>
                    <Badge variant="outline" className="text-xs">
                      {activity.timestamp}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{activity.customerInfo}</p>
                  {activity.details && <p className="text-xs text-muted-foreground mt-1">{activity.details}</p>}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
