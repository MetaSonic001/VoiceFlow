"use client"

import React, { useState } from 'react'
import { Bot, User, Target, MessageSquare } from 'lucide-react'
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent } from "@/components/ui/card"

const agentRoles = [
  {
    id: 'support',
    title: 'Customer Support',
    description: 'Handle customer inquiries, troubleshooting, and support tickets',
    icon: MessageSquare
  },
  {
    id: 'sales',
    title: 'Sales Assistant',
    description: 'Qualify leads, schedule demos, and support sales processes',
    icon: Target
  },
  {
    id: 'hr',
    title: 'HR Assistant',
    description: 'Handle employee queries, benefits, policies, and onboarding',
    icon: User
  },
  {
    id: 'receptionist',
    title: 'Virtual Receptionist',
    description: 'Route calls, schedule appointments, and provide basic information',
    icon: Bot
  }
]

interface AgentCreationStepProps {
  data: Record<string, any>
  initialData?: Record<string, any>
  onDataChange: (data: Record<string, any>) => void
  onNext: () => void
  onPrevious: () => void
  canGoNext: boolean
  canGoPrevious: boolean
}

export function AgentCreationStep({ data, onDataChange, initialData }: AgentCreationStepProps) {
  const [formData, setFormData] = useState(() => ({
    agentName: initialData?.agentName ?? data.agentName ?? '',
    agentRole: initialData?.agentRole ?? data.agentRole ?? '',
    agentDescription: initialData?.agentDescription ?? data.agentDescription ?? '',
    ...data,
    ...(initialData || {})
  }))

  const handleInputChange = (field: string, value: string) => {
    const newData = { ...formData, [field]: value }
    setFormData(newData)
    onDataChange(newData)
  }

  const selectedRole = agentRoles.find(role => role.id === formData.agentRole)

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl sm:text-2xl font-bold">Create your AI agent</h2>
        <p className="text-sm sm:text-base text-muted-foreground">Give your agent a name and define its primary role</p>
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="agentName">Agent Name</Label>
          <div className="relative">
            <Bot className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              id="agentName"
              type="text"
              value={formData.agentName}
              onChange={(e) => handleInputChange('agentName', e.target.value)}
              placeholder="e.g., Sarah, Alex, or CustomerBot"
              className="pl-10"
              required
            />
          </div>
        </div>

        <div className="space-y-4">
          <Label>Agent Role</Label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
            {agentRoles.map(role => {
              const IconComponent = role.icon
              return (
                <Card
                  key={role.id}
                  className={`cursor-pointer transition-all hover:shadow-md ${
                    formData.agentRole === role.id
                      ? 'ring-2 ring-primary bg-primary/5'
                      : 'hover:border-primary/50'
                  }`}
                  onClick={() => handleInputChange('agentRole', role.id)}
                >
                  <CardContent className="p-3 sm:p-4">
                    <div className="flex items-start space-x-3">
                      <div className={`p-2 rounded-lg flex-shrink-0 ${
                        formData.agentRole === role.id 
                          ? 'bg-primary text-primary-foreground' 
                          : 'bg-muted text-muted-foreground'
                      }`}>
                        <IconComponent className="h-4 w-4 sm:h-5 sm:w-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm sm:text-base truncate">{role.title}</h3>
                        <p className="text-xs sm:text-sm text-muted-foreground">{role.description}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>

        {selectedRole && (
          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="p-3 sm:p-4">
              <div className="flex items-center space-x-3">
                <div className="bg-primary text-primary-foreground p-2 rounded-lg flex-shrink-0">
                  <selectedRole.icon className="h-4 w-4 sm:h-5 sm:w-5" />
                </div>
                <div className="min-w-0">
                  <h4 className="font-medium text-primary text-sm sm:text-base">{selectedRole.title}</h4>
                  <p className="text-xs sm:text-sm text-primary/70">{selectedRole.description}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="space-y-2">
          <Label htmlFor="agentDescription">Description (Optional)</Label>
          <Textarea
            id="agentDescription"
            value={formData.agentDescription}
            onChange={(e) => handleInputChange('agentDescription', e.target.value)}
            placeholder="Describe what specific tasks this agent should handle..."
            rows={3}
            className="resize-none"
          />
        </div>
      </div>
    </div>
  )
}