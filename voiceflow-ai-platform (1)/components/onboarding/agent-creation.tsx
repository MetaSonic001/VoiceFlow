"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useToast } from '@/hooks/use-toast'
import { Button } from "@/components/ui/button"
import MotionWrapper from '@/components/ui/MotionWrapper'
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Bot, Phone, MessageSquare, Mail } from "lucide-react"

interface AgentCreationProps {
  onComplete: (data: any) => void
  data?: Record<string, any>
  initialData?: Record<string, any>
}

export function AgentCreation({ onComplete, data, initialData }: AgentCreationProps) {
  const [formData, setFormData] = useState(() => ({
    agentName: "",
    role: "",
    description: "",
    channels: [] as string[],
    ...(initialData?.agent || {}),
  }))
  const { toast } = useToast()

  useEffect(() => {
    // If parent provides server data after mount, hydrate form
    if (data?.agent) {
      setFormData((prev: any) => ({ ...prev, ...data.agent }))
    }
  }, [data])

  const channels = [
    { id: "phone", label: "Phone Calls", icon: Phone, description: "Handle inbound and outbound voice calls" },
    { id: "chat", label: "Website Chat", icon: MessageSquare, description: "Embed chat widget on your website" },
    { id: "whatsapp", label: "WhatsApp", icon: MessageSquare, description: "Connect via WhatsApp Business API" },
    { id: "email", label: "Email", icon: Mail, description: "Respond to email inquiries" },
  ]

  const handleChannelChange = (channelId: string, checked: boolean) => {
    if (checked) {
      setFormData({ ...formData, channels: [...formData.channels, channelId] })
    } else {
      setFormData({ ...formData, channels: formData.channels.filter((c: string) => c !== channelId) })
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Parent wizard handles server persistence; just emit data upward
    toast({ title: 'Agent saved', description: 'Agent details saved locally' })
    onComplete({ agent: formData })
  }

  return (
    <MotionWrapper>
      <div className="space-y-6">
      <div className="text-center">
        <Bot className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Create your AI agent</h2>
        <p className="text-muted-foreground">
          Give your agent a name, role, and choose how customers will interact with it.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="agentName">Agent Name *</Label>
            <Input
              id="agentName"
              placeholder="e.g., Sarah, Customer Support Assistant"
              value={formData.agentName}
              onChange={(e) => setFormData({ ...formData, agentName: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Agent Role *</Label>
            <Input
              id="role"
              placeholder="e.g., Customer Support Specialist, Sales Assistant"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Agent Description</Label>
            <Textarea
              id="description"
              placeholder="Describe what your agent should do and how it should behave..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
            />
          </div>
        </div>

        <div className="space-y-4">
          <Label>Communication Channels *</Label>
          <p className="text-sm text-muted-foreground">Select how customers will interact with your agent</p>
          <div className="grid md:grid-cols-2 gap-4">
            {channels.map((channel) => (
              <div key={channel.id} className="flex items-start space-x-3 p-4 border border-border rounded-lg">
                <Checkbox
                  id={channel.id}
                  checked={formData.channels.includes(channel.id)}
                  onCheckedChange={(checked) => handleChannelChange(channel.id, checked as boolean)}
                />
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <channel.icon className="w-4 h-4 text-accent" />
                    <Label htmlFor={channel.id} className="font-medium">
                      {channel.label}
                    </Label>
                  </div>
                  <p className="text-sm text-muted-foreground">{channel.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={!formData.agentName || !formData.role || formData.channels.length === 0}
        >
          Continue to Knowledge Upload
        </Button>
      </form>
      </div>
    </MotionWrapper>
  )
}
