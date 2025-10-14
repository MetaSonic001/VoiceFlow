"use client"

import React, { useState } from 'react'
import { Phone, MessageSquare, Hash, Slack, Check, Settings } from 'lucide-react'
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
    <div className="w-full max-w-4xl mx-auto">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Setup Communication Channels</h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Choose how customers will interact with your agent
          </p>
        </div>

        {/* Channel Selection Grid */}
        <div>
          <Label className="text-base font-medium mb-4 block">Select Channels</Label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {channelOptions.map(channel => {
              const IconComponent = channel.icon
              const isSelected = selectedChannels.includes(channel.id)

              return (
                <Card
                  key={channel.id}
                  className={`cursor-pointer transition-all duration-200 hover:shadow-lg ${isSelected
                      ? 'ring-2 ring-primary bg-primary/5 border-primary'
                      : 'hover:border-primary/50'
                    }`}
                  onClick={() => handleChannelToggle(channel.id)}
                >
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-4 flex-1 min-w-0">
                        <div className={`p-3 rounded-xl transition-colors ${isSelected
                            ? 'bg-primary text-primary-foreground shadow-sm'
                            : 'bg-muted text-muted-foreground'
                          }`}>
                          <IconComponent className="h-6 w-6" />
                        </div>
                        <div className="flex-1 min-w-0 space-y-1">
                          <h3 className="font-semibold text-base leading-tight">
                            {channel.title}
                          </h3>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {channel.description}
                          </p>
                        </div>
                      </div>
                      {isSelected && (
                        <div className="bg-primary text-primary-foreground p-1.5 rounded-full flex-shrink-0">
                          <Check className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>

        {/* Configuration Cards */}
        <div className="space-y-6">
          {/* Phone Setup */}
          {selectedChannels.includes('phone') && (
            <Card className="shadow-sm border-primary/20">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Phone className="h-5 w-5 text-primary" />
                  <span>Phone Number Setup</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <Label htmlFor="preferredArea" className="text-base font-medium">
                      Preferred Area Code
                    </Label>
                    <Input
                      id="preferredArea"
                      placeholder="e.g., 555, 212, 415"
                      value={phoneSetup.preferredArea}
                      onChange={(e) => handlePhoneSetupChange('preferredArea', e.target.value)}
                      className="h-11"
                    />
                    <p className="text-sm text-muted-foreground">
                      Choose a local area code for your customers
                    </p>
                  </div>
                  <div className="space-y-3">
                    <Label htmlFor="businessHours" className="text-base font-medium">
                      Availability
                    </Label>
                    <Select
                      value={phoneSetup.businessHours}
                      onValueChange={(value) => handlePhoneSetupChange('businessHours', value)}
                    >
                      <SelectTrigger className="h-11">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="24/7">24/7 Available</SelectItem>
                        <SelectItem value="business">Business Hours Only</SelectItem>
                        <SelectItem value="custom">Custom Schedule</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-sm text-muted-foreground">
                      When should your agent be available?
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Chat Widget Setup */}
          {selectedChannels.includes('chat') && (
            <Card className="shadow-sm border-primary/20">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <MessageSquare className="h-5 w-5 text-primary" />
                  <span>Chat Widget Configuration</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="space-y-1">
                      <Label className="text-base font-medium">Show Agent Avatar</Label>
                      <p className="text-sm text-muted-foreground">Display agent profile picture</p>
                    </div>
                    <Switch defaultChecked />
                  </div>
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="space-y-1">
                      <Label className="text-base font-medium">Proactive Messages</Label>
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
            <Card className="shadow-sm border-primary/20">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Hash className="h-5 w-5 text-primary" />
                  <span>WhatsApp Business Setup</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 p-5 rounded-lg">
                  <div className="flex gap-3">
                    <Settings className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="font-medium text-blue-900 dark:text-blue-100">Verification Required</p>
                      <p className="text-sm text-blue-800 dark:text-blue-200 leading-relaxed">
                        WhatsApp Business integration requires verification and approval from Meta.
                        We'll guide you through the process after setup completion.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Slack Setup */}
          {selectedChannels.includes('slack') && (
            <Card className="shadow-sm border-primary/20">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Slack className="h-5 w-5 text-primary" />
                  <span>Slack Integration Setup</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <Label htmlFor="slackWorkspace" className="text-base font-medium">
                    Slack Workspace URL
                  </Label>
                  <Input
                    id="slackWorkspace"
                    placeholder="your-workspace.slack.com"
                    className="h-11"
                  />
                  <p className="text-sm text-muted-foreground">
                    Enter your Slack workspace domain
                  </p>
                </div>
                <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 p-5 rounded-lg">
                  <div className="flex gap-3">
                    <Settings className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <p className="font-medium text-amber-900 dark:text-amber-100">Admin Access Needed</p>
                      <p className="text-sm text-amber-800 dark:text-amber-200 leading-relaxed">
                        You'll need admin permissions to install the VoiceFlow bot in your Slack workspace.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Summary Card */}
        <Card className="bg-primary/5 border-primary/30 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg text-primary">
              <Check className="h-5 w-5" />
              <span>Channel Summary</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-primary">Selected Channels:</span>
              <span className="text-2xl font-bold text-primary">{selectedChannels.length}</span>
            </div>
            {selectedChannels.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {selectedChannels.map(channelId => {
                  const channel = channelOptions.find(c => c.id === channelId)
                  const IconComponent = channel?.icon || Phone
                  return (
                    <div
                      key={channelId}
                      className="flex items-center gap-2 bg-primary text-primary-foreground px-3 py-2 rounded-lg text-sm font-medium"
                    >
                      <IconComponent className="h-4 w-4" />
                      {channel?.title}
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

