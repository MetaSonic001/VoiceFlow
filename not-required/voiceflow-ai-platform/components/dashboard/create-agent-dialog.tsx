"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Bot } from "lucide-react"
import { useRouter } from "next/navigation"

interface CreateAgentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateAgentDialog({ open, onOpenChange }: CreateAgentDialogProps) {
  const [formData, setFormData] = useState({
    name: "",
    role: "",
    description: "",
    useCase: "",
  })
  const [loading, setLoading] = useState(false)
  const router: Router= useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))

    // Redirect to onboarding for the new agent
    onOpenChange(false)
    router.push("/onboarding")
    setLoading(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center">
              <Bot className="w-6 h-6 text-primary-foreground" />
            </div>
          </div>
          <DialogTitle className="text-2xl">Create New Agent</DialogTitle>
          <DialogDescription>Set up a new AI agent to handle customer interactions</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Agent Name</Label>
            <Input
              id="name"
              placeholder="e.g., Customer Support Assistant"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Agent Role</Label>
            <Input
              id="role"
              placeholder="e.g., Customer Support Specialist"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="useCase">Primary Use Case</Label>
            <Select value={formData.useCase} onValueChange={(value) => setFormData({ ...formData, useCase: value })}>
              <SelectTrigger>
                <SelectValue placeholder="Select primary use case" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="customer-support">Customer Support</SelectItem>
                <SelectItem value="sales-lead-qualification">Sales & Lead Qualification</SelectItem>
                <SelectItem value="appointment-scheduling">Appointment Scheduling</SelectItem>
                <SelectItem value="hr-internal-helpdesk">HR & Internal Helpdesk</SelectItem>
                <SelectItem value="order-status-tracking">Order Status & Tracking</SelectItem>
                <SelectItem value="general-inquiries">General Business Inquiries</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Textarea
              id="description"
              placeholder="Describe what this agent should do..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>

          <div className="flex space-x-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !formData.name || !formData.role} className="flex-1">
              {loading ? "Creating..." : "Create Agent"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
