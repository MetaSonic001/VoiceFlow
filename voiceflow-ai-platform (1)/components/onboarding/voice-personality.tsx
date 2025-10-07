"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Volume2, Play } from "lucide-react"

interface VoicePersonalityProps {
  onComplete: (data: any) => void
  data?: Record<string, any>
  initialData?: Record<string, any>
}

export function VoicePersonality({ onComplete, data, initialData }: VoicePersonalityProps) {
  const [formData, setFormData] = useState<Record<string, any>>(() => ({
    voice: "",
    tone: "",
    personality: "",
    language: "en-US",
    ...(initialData?.voicePersonality || {}),
  }))

  // hydrate if parent provides server data later
    useEffect(() => {
      if (data?.voicePersonality) setFormData(prev => ({ ...prev, ...data.voicePersonality }))
    }, [data])

  const voices = [
    { id: "sarah", name: "Sarah", description: "Professional female voice, clear and friendly" },
    { id: "james", name: "James", description: "Professional male voice, warm and confident" },
    { id: "emma", name: "Emma", description: "Youthful female voice, energetic and approachable" },
    { id: "david", name: "David", description: "Mature male voice, authoritative and trustworthy" },
  ]

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

  const playVoiceSample = (voiceId: string) => {
    // In a real implementation, this would play a voice sample
    console.log(`Playing voice sample for: ${voiceId}`)
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
        {/* Voice Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Voice Selection</CardTitle>
            <CardDescription>Choose the voice that best represents your brand</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              {voices.map((voice) => (
                <div
                  key={voice.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    formData.voice === voice.id ? "border-accent bg-accent/10" : "border-border hover:border-accent/50"
                  }`}
                  onClick={() => setFormData({ ...formData, voice: voice.id })}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium">{voice.name}</h3>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        playVoiceSample(voice.id)
                      }}
                    >
                      <Play className="w-4 h-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">{voice.description}</p>
                </div>
              ))}
            </div>
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

        <Button type="submit" className="w-full" disabled={!formData.voice || !formData.tone}>
          Continue to Channel Setup
        </Button>
      </form>
    </div>
  )
}
// Minimal, environment-safe shim for useEffect when the real React hook isn't imported.
// It performs a simple shallow-dependency comparison and runs the effect when deps change.
// This is a pragmatic fallback for the specific usage in this file (hydration on data change).
// Note: In a real React app prefer importing useEffect from "react".
function useEffect(
  effect: () => void | (() => void),
  deps?: (Record<string, any> | undefined)[]
) {
  const globalKey = "__shim_useEffect_store__"
  if (!(globalKey in globalThis)) {
    ;(globalThis as any)[globalKey] = {
      depsMap: new Map<Function, any[]>(),
      cleanupMap: new Map<Function, (() => void) | undefined>(),
    }
  }
  const store = (globalThis as any)[globalKey] as {
    depsMap: Map<Function, any[]>
    cleanupMap: Map<Function, (() => void) | undefined>
  }

  const prevDeps = store.depsMap.get(effect)
  const depsChanged = !areDepsEqual(prevDeps, deps)

  if (!depsChanged) return

  // run previous cleanup if present
  const prevCleanup = store.cleanupMap.get(effect)
  if (typeof prevCleanup === "function") {
    try {
      prevCleanup()
    } catch {
      /* ignore cleanup errors */
    }
    store.cleanupMap.delete(effect)
  }

  // run effect asynchronously to better mimic React's effect timing
  Promise.resolve().then(() => {
    const maybeCleanup = effect()
    if (typeof maybeCleanup === "function") {
      store.cleanupMap.set(effect, maybeCleanup)
    } else {
      store.cleanupMap.delete(effect)
    }
  })

  store.depsMap.set(effect, deps ?? [])
}

function areDepsEqual(a?: any[], b?: any[]) {
  if (a === b) return true
  if (!a || !b) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (!Object.is(a[i], b[i])) return false
  }
  return true
}

