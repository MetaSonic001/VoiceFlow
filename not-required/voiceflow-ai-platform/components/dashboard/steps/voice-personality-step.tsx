"use client"

import React, { useState } from 'react'
import { Volume2, User, MessageCircle, Play, Pause, Sparkles } from 'lucide-react'
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
  initialData?: Record<string, any>
  onDataChange: (data: Record<string, any>) => void
  onNext: () => void
  onPrevious: () => void
  canGoNext: boolean
  canGoPrevious: boolean
}

export function VoicePersonalityStep({ data, onDataChange, initialData }: VoicePersonalityStepProps) {
  const [selectedVoice, setSelectedVoice] = useState(initialData?.selectedVoice ?? data.selectedVoice ?? '')
  const [selectedPersonality, setSelectedPersonality] = useState(initialData?.selectedPersonality ?? data.selectedPersonality ?? '')
  const [customInstructions, setCustomInstructions] = useState(initialData?.customInstructions ?? data.customInstructions ?? '')
  const [playingVoice, setPlayingVoice] = useState<string | null>(null)

  const handleVoicePlay = (voiceId: string) => {
    if (playingVoice === voiceId) {
      setPlayingVoice(null)
    } else {
      setPlayingVoice(voiceId)
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
    const merged = { ...data, ...(initialData || {}), selectedVoice, selectedPersonality, customInstructions, ...newData }
    onDataChange(merged)
  }

  const selectedVoiceData = voiceOptions.find(v => v.id === selectedVoice)
  const selectedPersonalityData = personalityOptions.find(p => p.id === selectedPersonality)

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Voice & Personality</h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Configure how your agent sounds and behaves
          </p>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Voice Selection */}
          <Card className="shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Volume2 className="h-5 w-5 text-primary" />
                <span>Voice Selection</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-2">
                {voiceOptions.map(voice => {
                  const isSelected = selectedVoice === voice.id
                  const isPlaying = playingVoice === voice.id

                  return (
                    <Card
                      key={voice.id}
                      className={`cursor-pointer transition-all duration-200 hover:shadow-md ${isSelected
                          ? 'ring-2 ring-primary bg-primary/5 border-primary'
                          : 'hover:border-primary/50'
                        }`}
                      onClick={() => handleVoiceSelect(voice.id)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div className={`p-2.5 rounded-xl transition-colors ${isSelected
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted text-muted-foreground'
                              }`}>
                              <User className="h-5 w-5" />
                            </div>
                            <div className="flex-1 min-w-0 space-y-1">
                              <div className="font-semibold text-base">{voice.name}</div>
                              <div className="text-sm text-muted-foreground">
                                {voice.gender} • {voice.accent}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {voice.description}
                              </div>
                            </div>
                          </div>
                          <Button
                            variant={isPlaying ? "default" : "outline"}
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleVoicePlay(voice.id)
                            }}
                            className="flex-shrink-0 h-10 w-10"
                          >
                            {isPlaying ? (
                              <Pause className="h-4 w-4" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Personality Selection */}
          <Card className="shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg">
                <MessageCircle className="h-5 w-5 text-primary" />
                <span>Personality Type</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-2">
                {personalityOptions.map(personality => {
                  const isSelected = selectedPersonality === personality.id

                  return (
                    <Card
                      key={personality.id}
                      className={`cursor-pointer transition-all duration-200 hover:shadow-md ${isSelected
                          ? 'ring-2 ring-primary bg-primary/5 border-primary'
                          : 'hover:border-primary/50'
                        }`}
                      onClick={() => handlePersonalitySelect(personality.id)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className={`p-2.5 rounded-xl transition-colors ${isSelected
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted text-muted-foreground'
                            }`}>
                            <MessageCircle className="h-5 w-5" />
                          </div>
                          <div className="flex-1 min-w-0 space-y-1">
                            <div className="font-semibold text-base">
                              {personality.title}
                            </div>
                            <div className="text-sm text-muted-foreground leading-relaxed">
                              {personality.description}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Custom Instructions */}
        <Card className="shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-primary" />
              <span>Custom Instructions</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label htmlFor="instructions" className="text-base font-medium">
              Additional Personality Instructions
            </Label>
            <Textarea
              id="instructions"
              value={customInstructions}
              onChange={(e) => handleInstructionsChange(e.target.value)}
              placeholder="Add specific instructions for how your agent should behave, respond, or handle certain situations..."
              rows={4}
              className="resize-none text-base"
            />
            <p className="text-sm text-muted-foreground">
              Provide any additional guidance to customize your agent's behavior and responses
            </p>
          </CardContent>
        </Card>

        {/* Preview */}
        {(selectedVoice || selectedPersonality) && (
          <Card className="bg-primary/5 border-primary/20 shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg text-primary">
                <User className="h-5 w-5" />
                <span>Agent Preview</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {selectedVoiceData && (
                  <div className="flex items-start gap-2">
                    <span className="font-semibold text-primary min-w-[100px]">Voice:</span>
                    <span className="text-primary/80">
                      {selectedVoiceData.name} ({selectedVoiceData.accent} {selectedVoiceData.gender})
                    </span>
                  </div>
                )}
                {selectedPersonalityData && (
                  <div className="flex items-start gap-2">
                    <span className="font-semibold text-primary min-w-[100px]">Personality:</span>
                    <span className="text-primary/80">{selectedPersonalityData.title}</span>
                  </div>
                )}
                {customInstructions && (
                  <div className="flex items-start gap-2">
                    <span className="font-semibold text-primary min-w-[100px]">Instructions:</span>
                    <span className="text-primary/80 flex-1">{customInstructions}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

