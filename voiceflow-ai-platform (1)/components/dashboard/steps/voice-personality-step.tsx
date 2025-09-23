"use client"

import React, { useState } from 'react'
import { Volume2, User, MessageCircle, Play, Pause } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const voiceOptions = [
  { id: 'sarah', name: 'Sarah', gender: 'Female', accent: 'American', description: 'Professional and friendly' },
  { id: 'alex', name: 'Alex', gender: 'Male', accent: 'American', description: 'Confident and approachable' },
  { id: 'emma', name: 'Emma', gender: 'Female', accent: 'British', description: 'Elegant and articulate' },
  { id: 'james', name: 'James', gender: 'Male', accent: 'British', description: 'Authoritative and calm' },
]

const personalityOptions = [
  { id: 'professional', title: 'Professional', description: 'Formal, precise, and business-focused' },
  { id: 'friendly', title: 'Friendly', description: 'Warm, conversational, and approachable' },
  { id: 'empathetic', title: 'Empathetic', description: 'Understanding, supportive, and caring' },
  { id: 'sales-driven', title: 'Sales-Driven', description: 'Persuasive, enthusiastic, and goal-oriented' },
]

interface VoicePersonalityStepProps {
  data: Record<string, any>
  onDataChange: (data: Record<string, any>) => void
  onNext: () => void
  onPrevious: () => void
  canGoNext: boolean
  canGoPrevious: boolean
}

export function VoicePersonalityStep({ data, onDataChange }: VoicePersonalityStepProps) {
  const [selectedVoice, setSelectedVoice] = useState(data.selectedVoice || '')
  const [selectedPersonality, setSelectedPersonality] = useState(data.selectedPersonality || '')
  const [customInstructions, setCustomInstructions] = useState(data.customInstructions || '')
  const [playingVoice, setPlayingVoice] = useState<string | null>(null)

  const handleVoicePlay = (voiceId: string) => {
    if (playingVoice === voiceId) {
      setPlayingVoice(null)
    } else {
      setPlayingVoice(voiceId)
      // Simulate audio playback
      setTimeout(() => setPlayingVoice(null), 3000)
    }
  }

  const handleVoiceSelect = (voiceId: string) => {
    setSelectedVoice(voiceId)
    updateData({ selectedVoice: voiceId })
  }

  const handlePersonalitySelect = (personalityId: string) => {
    setSelectedPersonality(personalityId)
    updateData({ selectedPersonality: personalityId })
  }

  const handleInstructionsChange = (instructions: string) => {
    setCustomInstructions(instructions)
    updateData({ customInstructions: instructions })
  }

  const updateData = (newData: Record<string, any>) => {
    onDataChange({
      ...data,
      selectedVoice,
      selectedPersonality,
      customInstructions,
      ...newData
    })
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl sm:text-2xl font-bold">Voice & Personality</h2>
        <p className="text-sm sm:text-base text-muted-foreground">Configure how your agent sounds and behaves</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Voice Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
              <Volume2 className="h-4 w-4 sm:h-5 sm:w-5" />
              <span>Voice Selection</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 sm:space-y-4">
            {voiceOptions.map(voice => (
              <Card
                key={voice.id}
                className={`cursor-pointer transition-all ${
                  selectedVoice === voice.id
                    ? 'ring-2 ring-primary bg-primary/5'
                    : 'hover:shadow-md'
                }`}
                onClick={() => handleVoiceSelect(voice.id)}
              >
                <CardContent className="p-3 sm:p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <div className={`p-1.5 sm:p-2 rounded-full flex-shrink-0 ${
                        selectedVoice === voice.id ? 'bg-primary text-primary-foreground' : 'bg-muted'
                      }`}>
                        <User className="h-3 w-3 sm:h-4 sm:w-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="font-medium text-sm sm:text-base">{voice.name}</div>
                        <div className="text-xs sm:text-sm text-muted-foreground">
                          {voice.gender} • {voice.accent}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">{voice.description}</div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleVoicePlay(voice.id)
                      }}
                      className="flex-shrink-0"
                    >
                      {playingVoice === voice.id ? (
                        <Pause className="h-3 w-3 sm:h-4 sm:w-4" />
                      ) : (
                        <Play className="h-3 w-3 sm:h-4 sm:w-4" />
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>

        {/* Personality Selection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
              <MessageCircle className="h-4 w-4 sm:h-5 sm:w-5" />
              <span>Personality Type</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 sm:space-y-4">
            {personalityOptions.map(personality => (
              <Card
                key={personality.id}
                className={`cursor-pointer transition-all ${
                  selectedPersonality === personality.id
                    ? 'ring-2 ring-primary bg-primary/5'
                    : 'hover:shadow-md'
                }`}
                onClick={() => handlePersonalitySelect(personality.id)}
              >
                <CardContent className="p-3 sm:p-4">
                  <div className="flex items-start space-x-3">
                    <div className={`p-1.5 sm:p-2 rounded-full flex-shrink-0 ${
                      selectedPersonality === personality.id ? 'bg-primary text-primary-foreground' : 'bg-muted'
                    }`}>
                      <MessageCircle className="h-3 w-3 sm:h-4 sm:w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-sm sm:text-base">{personality.title}</div>
                      <div className="text-xs sm:text-sm text-muted-foreground">{personality.description}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Custom Instructions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base sm:text-lg">Custom Instructions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="instructions" className="text-sm">Additional Personality Instructions</Label>
            <Textarea
              id="instructions"
              value={customInstructions}
              onChange={(e) => handleInstructionsChange(e.target.value)}
              placeholder="Add specific instructions for how your agent should behave, respond, or handle certain situations..."
              rows={4}
              className="resize-none text-sm"
            />
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      {(selectedVoice || selectedPersonality) && (
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader>
            <CardTitle className="text-primary text-base sm:text-lg">Agent Preview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {selectedVoice && (
                <div className="text-sm">
                  <span className="font-medium">Voice:</span> {voiceOptions.find(v => v.id === selectedVoice)?.name} 
                  ({voiceOptions.find(v => v.id === selectedVoice)?.accent})
                </div>
              )}
              {selectedPersonality && (
                <div className="text-sm">
                  <span className="font-medium">Personality:</span> {personalityOptions.find(p => p.id === selectedPersonality)?.title}
                </div>
              )}
              {customInstructions && (
                <div className="text-sm">
                  <span className="font-medium">Custom Instructions:</span> {customInstructions}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}