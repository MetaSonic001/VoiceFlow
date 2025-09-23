"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Brain, Bot, BarChart3, Settings, HelpCircle, LogOut, Users, Phone } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"

export function DashboardSidebar() {
  const [activeItem, setActiveItem] = useState("agents")
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const router = useRouter()

  const menuItems = [
    { id: "agents", label: "AI Agents", icon: Bot, badge: "3", href: "/dashboard" },
    { id: "analytics", label: "Analytics", icon: BarChart3, href: "/dashboard/analytics" },
    { id: "calls", label: "Call Logs", icon: Phone, href: "/dashboard/calls" },
    { id: "team", label: "Team", icon: Users },
    { id: "settings", label: "Settings", icon: Settings },
  ]

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      // Mock logout - simulate API call
      await new Promise(resolve => setTimeout(resolve, 500))
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      // Clear local storage
      localStorage.removeItem("auth_token")
      localStorage.removeItem("session_id")
      localStorage.removeItem("user")

      // Redirect to home page
      router.push("/")
      setIsLoggingOut(false)
    }
  }

  return (
    <div className="fixed left-0 top-0 h-full w-64 bg-sidebar border-r border-sidebar-border">
      {/* Header */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-sidebar-primary rounded-lg flex items-center justify-center">
            <Brain className="w-5 h-5 text-sidebar-primary-foreground" />
          </div>
          <span className="text-xl font-bold text-sidebar-foreground">VoiceFlow AI</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2">
        {menuItems.map((item) => (
          <Link href={item.href || "#"} key={item.id}>
            <Button
              variant={activeItem === item.id ? "secondary" : "ghost"}
              className={`w-full justify-start ${
                activeItem === item.id
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              }`}
              onClick={() => setActiveItem(item.id)}
            >
              <item.icon className="w-4 h-4 mr-3" />
              {item.label}
              {item.badge && (
                <Badge variant="secondary" className="ml-auto">
                  {item.badge}
                </Badge>
              )}
            </Button>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-sidebar-border">
        <div className="space-y-2">
          <Button variant="ghost" className="w-full justify-start text-sidebar-foreground">
            <HelpCircle className="w-4 h-4 mr-3" />
            Help & Support
          </Button>
          <Button
            variant="ghost"
            className="w-full justify-start text-sidebar-foreground"
            onClick={handleLogout}
            disabled={isLoggingOut}
          >
            <LogOut className="w-4 h-4 mr-3" />
            {isLoggingOut ? "Signing Out..." : "Sign Out"}
          </Button>
        </div>
      </div>
    </div>
  )
}
