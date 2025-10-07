"use client"

import React, { useState } from 'react'
import { Phone, MessageSquare, Hash, Slack, Check } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"

const channelOptions = [
  {
    id: 'phone',
    title: 'Phone Number',
    description: 'Dedicated phone line for voice calls',
    icon: Phone,
    setup: true
  },
  {
    id: 'chat',
    title: 'Website Chat Widget',
    description: 'Embeddable chat widget for your website',
    icon: MessageSquare,
    setup: false
  },
  {
    id: 'whatsapp',
    title: 'WhatsApp Business',
    description: 'Connect via WhatsApp Business API',
    icon: Hash,
    setup: true
  },
  {
    id: 'slack',
    title: 'Slack Integration',
    description: 'Internal Slack bot for employees',
    icon: Slack,
    setup: true
  }
]

interface ChannelSetupStepProps {
  data: Record<string, any>
  initialData?: Record<string, any>
  onDataChange: (data: Record<string, any>) => void
  onNext: () => void
  onPrevious: () => void
  canGoNext: boolean
  canGoPrevious: boolean
}

export function ChannelSetupStep({ data, onDataChange, initialData }: ChannelSetupStepProps) {
  const [selectedChannels, setSelectedChannels] = useState<string[]>(initialData?.selectedChannels ?? data.selectedChannels ?? ['phone'])
  const [phoneSetup, setPhoneSetup] = useState(() => ({
    preferredArea: initialData?.phoneSetup?.preferredArea ?? data.phoneSetup?.preferredArea ?? '',
    businessHours: initialData?.phoneSetup?.businessHours ?? data.phoneSetup?.businessHours ?? 'business',
    ...data.phoneSetup,
    ...(initialData?.phoneSetup || {})
  }))

  const handleChannelToggle = (channelId: string) => {
    const newChannels = selectedChannels.includes(channelId)
      ? selectedChannels.filter(id => id !== channelId)
      : [...selectedChannels, channelId]
    
    setSelectedChannels(newChannels)
    updateData({ selectedChannels: newChannels })
  }

  const handlePhoneSetupChange = (field: string, value: string) => {
    const newPhoneSetup = { ...phoneSetup, [field]: value }
    setPhoneSetup(newPhoneSetup)
    updateData({ phoneSetup: newPhoneSetup })
  }

  const updateData = (newData: Record<string, any>) => {
    const merged = { ...data, ...(initialData || {}), selectedChannels, phoneSetup, ...newData }
    onDataChange(merged)
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl sm:text-2xl font-bold">Setup Communication Channels</h2>
        <p className="text-sm sm:text-base text-muted-foreground">Choose how customers will interact with your agent</p>
      </div>

      {/* Channel Selection */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
        {channelOptions.map(channel => {
          const IconComponent = channel.icon
          const isSelected = selectedChannels.includes(channel.id)
          
          return (
            <Card
              key={channel.id}
              className={`cursor-pointer transition-all ${
                isSelected
                  ? 'ring-2 ring-primary bg-primary/5'
                  : 'hover:shadow-md'
              }`}
              onClick={() => handleChannelToggle(channel.id)}
            >
              <CardContent className="p-3 sm:p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1 min-w-0">
                    <div className={`p-1.5 sm:p-2 rounded-lg flex-shrink-0 ${
                      isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    }`}>
                      <IconComponent className="h-4 w-4 sm:h-5 sm:w-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-sm sm:text-base">{channel.title}</h3>
                      <p className="text-xs sm:text-sm text-muted-foreground">{channel.description}</p>
                    </div>
                  </div>
                  {isSelected && (
                    <div className="bg-primary text-primary-foreground p-1 rounded-full">
                      <Check className="h-3 w-3" />
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Phone Setup */}
      {selectedChannels.includes('phone') && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Phone className="h-5 w-5" />
              <span>Phone Number Setup</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="preferredArea">Preferred Area Code</Label>
                <Input
                  id="preferredArea"
                  placeholder="e.g., 555, 212, 415"
                  value={phoneSetup.preferredArea}
                  onChange={(e) => handlePhoneSetupChange('preferredArea', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="businessHours">Availability</Label>
                <Select
                  value={phoneSetup.businessHours}
                  onValueChange={(value) => handlePhoneSetupChange('businessHours', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="24/7">24/7 Available</SelectItem>
                    <SelectItem value="business">Business Hours Only</SelectItem>
                    <SelectItem value="custom">Custom Schedule</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chat Widget Setup */}
      {selectedChannels.includes('chat') && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="h-5 w-5" />
              <span>Chat Widget Configuration</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Show Agent Avatar</Label>
                  <p className="text-sm text-muted-foreground">Display agent profile picture</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Proactive Messages</Label>
                  <p className="text-sm text-muted-foreground">Send greeting messages</p>
                </div>
                <Switch defaultChecked />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* WhatsApp Setup */}
      {selectedChannels.includes('whatsapp') && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Hash className="h-5 w-5" />
              <span>WhatsApp Business Setup</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted p-4 rounded-lg">
              <p className="text-sm">
                WhatsApp Business integration requires verification and approval from Meta. 
                We'll guide you through the process after setup completion.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Slack Setup */}
      {selectedChannels.includes('slack') && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Slack className="h-5 w-5" />
              <span>Slack Integration Setup</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="slackWorkspace">Slack Workspace URL</Label>
              <Input
                id="slackWorkspace"
                placeholder="your-workspace.slack.com"
                />
            </div>
            <div className="bg-muted p-4 rounded-lg">
              <p className="text-sm">
                You'll need admin permissions to install the VoiceFlow bot in your Slack workspace.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      <Card className="bg-primary/5 border-primary/20">
        <CardHeader>
          <CardTitle className="text-primary">Channel Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p className="text-sm">
              <span className="font-medium">Selected Channels:</span> {selectedChannels.length}
            </p>
            <div className="flex flex-wrap gap-2">
              {selectedChannels.map(channelId => {
                const channel = channelOptions.find(c => c.id === channelId)
                return (
                  <div key={channelId} className="bg-primary text-primary-foreground px-2 py-1 rounded text-xs">
                    {channel?.title}
                  </div>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}