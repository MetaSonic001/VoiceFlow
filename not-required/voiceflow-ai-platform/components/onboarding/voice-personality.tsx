"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Volume2 } from "lucide-react"
import { VoiceSelector } from "@/components/voice-selector"

interface VoicePersonalityProps {
  onComplete: (data: any) => void
  data?: Record<string, any>
  initialData?: Record<string, any>
}

export function VoicePersonality({ onComplete, data, initialData }: VoicePersonalityProps) {
  const [formData, setFormData] = useState<Record<string, any>>(() => ({
    voiceId: null,
    tone: "",
    personality: "",
    language: "en-US",
    ...(initialData?.voicePersonality || {}),
  }))

  useEffect(() => {
    if (data?.voicePersonality) setFormData(prev => ({ ...prev, ...data.voicePersonality }))
  }, [data])

  const tones = [
    { id: "professional", name: "Professional", description: "Formal, business-appropriate tone" },
    { id: "friendly", name: "Friendly", description: "Warm and approachable, casual but respectful" },
    { id: "empathetic", name: "Empathetic", description: "Understanding and supportive tone" },
    { id: "sales-driven", name: "Sales-Driven", description: "Persuasive and goal-oriented" },
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onComplete({ voicePersonality: formData })
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Volume2 className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Choose voice and personality</h2>
        <p className="text-muted-foreground">
          Select how your agent should sound and behave when interacting with customers.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Voice Selection — powered by Chatterbox TTS */}
        <Card>
          <CardHeader>
            <CardTitle>Voice Selection</CardTitle>
            <CardDescription>
              Choose a preset voice or clone a custom one from a short audio sample
            </CardDescription>
          </CardHeader>
          <CardContent>
            <VoiceSelector
              value={formData.voiceId}
              onChange={(voiceId) => setFormData({ ...formData, voiceId })}
            />
          </CardContent>
        </Card>

        {/* Tone & Personality */}
        <Card>
          <CardHeader>
            <CardTitle>Tone & Personality</CardTitle>
            <CardDescription>Define how your agent should communicate</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Communication Tone</Label>
              <Select value={formData.tone} onValueChange={(value) => setFormData({ ...formData, tone: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select communication tone" />
                </SelectTrigger>
                <SelectContent>
                  {tones.map((tone) => (
                    <SelectItem key={tone.id} value={tone.id}>
                      <div>
                        <div className="font-medium">{tone.name}</div>
                        <div className="text-sm text-muted-foreground">{tone.description}</div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Language</Label>
              <Select
                value={formData.language}
                onValueChange={(value) => setFormData({ ...formData, language: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en-US">English (US)</SelectItem>
                  <SelectItem value="en-GB">English (UK)</SelectItem>
                  <SelectItem value="es-ES">Spanish</SelectItem>
                  <SelectItem value="fr-FR">French</SelectItem>
                  <SelectItem value="de-DE">German</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Personality Instructions</Label>
              <Textarea
                placeholder="Describe how your agent should behave. For example: 'Be helpful and patient. Always ask clarifying questions if unsure. Use simple language and avoid technical jargon.'"
                value={formData.personality}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                rows={4}
              />
            </div>
          </CardContent>
        </Card>

        <Button type="submit" className="w-full" disabled={!formData.voiceId || !formData.tone}>
          Continue to Channel Setup
        </Button>
      </form>
    </div>
  )
}

