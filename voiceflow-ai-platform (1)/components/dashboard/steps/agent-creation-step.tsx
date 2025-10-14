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
    <div className="w-full h-full max-w-4xl mx-auto">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Create your AI agent</h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Give your agent a name and define its primary role
          </p>
        </div>

        {/* Form Content */}
        <div className="space-y-8">
          {/* Agent Name Input */}
          <div className="space-y-3">
            <Label htmlFor="agentName" className="text-base font-medium">
              Agent Name
            </Label>
            <div className="relative">
              <Bot className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                id="agentName"
                type="text"
                value={formData.agentName}
                onChange={(e) => handleInputChange('agentName', e.target.value)}
                placeholder="e.g., Sarah, Alex, or CustomerBot"
                className="pl-11 h-12 text-base"
                required
              />
            </div>
          </div>

          {/* Agent Role Selection */}
          <div className="space-y-4">
            <Label className="text-base font-medium">Agent Role</Label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agentRoles.map(role => {
                const IconComponent = role.icon
                const isSelected = formData.agentRole === role.id

                return (
                  <Card
                    key={role.id}
                    className={`cursor-pointer transition-all duration-200 hover:shadow-lg ${isSelected
                      ? 'ring-2 ring-primary bg-primary/5 border-primary'
                      : 'hover:border-primary/50 hover:bg-accent/5'
                      }`}
                    onClick={() => handleInputChange('agentRole', role.id)}
                  >
                    <CardContent className="p-5">
                      <div className="flex items-start gap-4">
                        <div className={`p-3 rounded-xl transition-colors ${isSelected
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'bg-muted text-muted-foreground'
                          }`}>
                          <IconComponent className="h-6 w-6" />
                        </div>
                        <div className="flex-1 min-w-0 space-y-1">
                          <h3 className="font-semibold text-base leading-tight">
                            {role.title}
                          </h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {role.description}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>

          {/* Selected Role Confirmation */}
          {selectedRole && (
            <Card className="bg-primary/5 border-primary/30 shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-center gap-4">
                  <div className="bg-primary text-primary-foreground p-3 rounded-xl shadow-sm">
                    <selectedRole.icon className="h-6 w-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-primary text-base mb-1">
                      Selected: {selectedRole.title}
                    </h4>
                    <p className="text-sm text-primary/80 leading-relaxed">
                      {selectedRole.description}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Description Textarea */}
          <div className="space-y-3">
            <Label htmlFor="agentDescription" className="text-base font-medium">
              Description <span className="text-muted-foreground font-normal">(Optional)</span>
            </Label>
            <Textarea
              id="agentDescription"
              value={formData.agentDescription}
              onChange={(e) => handleInputChange('agentDescription', e.target.value)}
              placeholder="Describe what specific tasks this agent should handle..."
              rows={4}
              className="resize-none text-base"
            />
            <p className="text-sm text-muted-foreground">
              Add any specific requirements or tasks for your agent
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

