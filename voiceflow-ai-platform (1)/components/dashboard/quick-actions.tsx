"use client"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Zap, Pause, Play, RefreshCw, Settings, BarChart3 } from "lucide-react"

export function QuickActions() {
  const handlePauseAll = () => {
    console.log("[v0] Pausing all agents")
    // TODO: Implement pause all agents functionality
  }

  const handleActivateAll = () => {
    console.log("[v0] Activating all agents")
    // TODO: Implement activate all agents functionality
  }

  const handleRefreshData = () => {
    console.log("[v0] Refreshing dashboard data")
    // TODO: Implement data refresh functionality
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Zap className="w-4 h-4 mr-2" />
          Quick Actions
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onClick={handlePauseAll}>
          <Pause className="w-4 h-4 mr-2" />
          Pause All Agents
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleActivateAll}>
          <Play className="w-4 h-4 mr-2" />
          Activate All Agents
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleRefreshData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh Data
        </DropdownMenuItem>
        <DropdownMenuItem>
          <BarChart3 className="w-4 h-4 mr-2" />
          Export Analytics
        </DropdownMenuItem>
        <DropdownMenuItem>
          <Settings className="w-4 h-4 mr-2" />
          System Settings
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
