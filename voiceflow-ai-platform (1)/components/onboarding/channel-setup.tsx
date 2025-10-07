"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Phone, MessageSquare, Mail, Copy, ExternalLink } from "lucide-react"
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/use-toast'

interface ChannelSetupProps {
  onComplete: (data: any) => void
}

export function ChannelSetup({ onComplete }: ChannelSetupProps) {
  const { toast } = useToast()

  const [formData, setFormData] = useState({
    phoneNumber: "",
    chatWidget: {
      enabled: true,
      websiteUrl: "",
      widgetColor: "#6366f1",
    },
    whatsapp: {
      enabled: false,
      businessNumber: "",
    },
    email: {
      enabled: false,
      forwardingAddress: "",
    },
  })

  const [availableNumbers, setAvailableNumbers] = useState<Array<{ sid?: string; phone_number?: string; friendly_name?: string }>>([])
  const [loadingNumbers, setLoadingNumbers] = useState(false)

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoadingNumbers(true)
      try {
        const data = await apiClient.getTwilioNumbers()
        if (mounted) setAvailableNumbers(data.numbers || [])
      } catch (e: any) {
        console.warn('Could not load Twilio numbers', e)
        toast({ title: 'Twilio', description: e?.message || 'Could not load numbers' })
      } finally {
        if (mounted) setLoadingNumbers(false)
      }
    }
    load()
    return () => { mounted = false }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // return selected channels + phone number to parent; parent will call backend API
    onComplete({ channels: formData, phone_number: formData.phoneNumber })
  }

  const copyWidgetCode = () => {
    const widgetCode = `<script src="https://voiceflow-ai.com/widget.js" data-agent-id="your-agent-id"></script>`
    navigator.clipboard.writeText(widgetCode)
    toast({ title: 'Copied', description: 'Widget embed code copied to clipboard' })
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <MessageSquare className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Configure communication channels</h2>
        <p className="text-muted-foreground">Set up how customers will reach your AI agent across different platforms.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Phone Setup */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Phone className="w-5 h-5" />
              <span>Phone Number</span>
              <Badge variant="secondary">Recommended</Badge>
            </CardTitle>
            <CardDescription>Get a dedicated phone number for your AI agent</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Assigned Phone Number</p>
                  <p className="text-sm text-muted-foreground">{formData.phoneNumber || 'Not assigned'}</p>
                </div>
                <Badge variant="outline">Active</Badge>
              </div>
            </div>

            <div className="mt-3">
              <Label>Choose a Twilio Number</Label>
              {loadingNumbers ? (
                <p>Loading numbers...</p>
              ) : (
                <div className="space-y-2">
                  {availableNumbers.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No Twilio numbers available. You can provision one in the Twilio console.</p>
                  ) : (
                    <div className="grid gap-2 grid-cols-1 md:grid-cols-2">
                      {availableNumbers.map((n) => (
                        <button
                          key={n.sid || n.phone_number}
                          type="button"
                          onClick={() => setFormData({ ...formData, phoneNumber: n.phone_number || '' })}
                          className={`p-3 border rounded text-left ${formData.phoneNumber === n.phone_number ? 'border-primary bg-muted' : 'border-border'}`}
                        >
                          <div className="font-medium">{n.phone_number}</div>
                          <div className="text-sm text-muted-foreground">{n.friendly_name}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <p className="text-sm text-muted-foreground">This number is automatically provisioned for your agent. Customers can call this number to interact with your AI agent.</p>
          </CardContent>
        </Card>

        {/* Chat Widget */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5" />
              <span>Website Chat Widget</span>
            </CardTitle>
            <CardDescription>Embed a chat widget on your website</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="websiteUrl">Website URL</Label>
              <Input
                id="websiteUrl"
                placeholder="https://yourwebsite.com"
                value={formData.chatWidget.websiteUrl}
                onChange={(e) => setFormData({ ...formData, chatWidget: { ...formData.chatWidget, websiteUrl: e.target.value } })}
              />
            </div>

            <div className="space-y-2">
              <Label>Widget Color</Label>
              <div className="flex items-center space-x-2">
                <Input
                  type="color"
                  value={formData.chatWidget.widgetColor}
                  onChange={(e) => setFormData({ ...formData, chatWidget: { ...formData.chatWidget, widgetColor: e.target.value } })}
                  className="w-12 h-10"
                />
                <Input value={formData.chatWidget.widgetColor} onChange={(e) => setFormData({ ...formData, chatWidget: { ...formData.chatWidget, widgetColor: e.target.value } })} className="flex-1" />
              </div>
            </div>

            <div className="p-4 bg-muted rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <Label>Embed Code</Label>
                <Button variant="ghost" size="sm" onClick={copyWidgetCode}>
                  <Copy className="w-4 h-4 mr-1" />
                  Copy
                </Button>
              </div>
              <code className="text-sm bg-background p-2 rounded block">{`<script src="https://voiceflow-ai.com/widget.js" data-agent-id="your-agent-id"></script>`}</code>
            </div>
          </CardContent>
        </Card>

        {/* WhatsApp */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5" />
              <span>WhatsApp Business</span>
              <Badge variant="outline">Optional</Badge>
            </CardTitle>
            <CardDescription>Connect your WhatsApp Business account</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 border border-dashed border-border rounded-lg text-center">
              <p className="text-sm text-muted-foreground mb-2">WhatsApp Business API integration</p>
              <Button variant="outline" size="sm">
                <ExternalLink className="w-4 h-4 mr-1" />
                Connect WhatsApp
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Email */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Mail className="w-5 h-5" />
              <span>Email Integration</span>
              <Badge variant="outline">Optional</Badge>
            </CardTitle>
            <CardDescription>Forward emails to your AI agent for automated responses</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="emailForwarding">Email Forwarding Address</Label>
              <Input id="emailForwarding" placeholder="support@yourcompany.com" value={formData.email.forwardingAddress} onChange={(e) => setFormData({ ...formData, email: { ...formData.email, forwardingAddress: e.target.value } })} />
              <p className="text-sm text-muted-foreground">Forward emails to: agent-12345@voiceflow-ai.com</p>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" className="w-full">
          Continue to Testing
        </Button>
      </form>
    </div>
  )
}
