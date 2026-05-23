'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Play, Plus, Trash2, Copy } from 'lucide-react'

interface Voice {
  id: string
  name: string
  language: string
  gender: 'male' | 'female' | 'neutral'
  accent: string
  speed: number
  pitch: number
  type: 'default' | 'custom'
}

const mockVoices: Voice[] = [
  {
    id: '1',
    name: 'Sarah',
    language: 'English (US)',
    gender: 'female',
    accent: 'American',
    speed: 1.0,
    pitch: 1.0,
    type: 'default',
  },
  {
    id: '2',
    name: 'Alex',
    language: 'English (US)',
    gender: 'male',
    accent: 'American',
    speed: 0.95,
    pitch: 0.95,
    type: 'default',
  },
  {
    id: '3',
    name: 'Emma',
    language: 'English (UK)',
    gender: 'female',
    accent: 'British',
    speed: 1.05,
    pitch: 1.05,
    type: 'default',
  },
  {
    id: '4',
    name: 'James',
    language: 'English (US)',
    gender: 'male',
    accent: 'American',
    speed: 0.9,
    pitch: 0.85,
    type: 'default',
  },
]

export default function VoiceLibraryPage() {
  const [voices, setVoices] = useState(mockVoices)
  const [playingId, setPlayingId] = useState<string | null>(null)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Voice Library
          </h1>
          <p className="text-muted-foreground font-mono">
            {voices.length} voices available
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Create Custom Voice
        </Button>
      </div>

      {/* Voices Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {voices.map((voice) => (
          <div key={voice.id} className="bg-card border border-border rounded-lg p-6">
            {/* Voice Header */}
            <div className="mb-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="text-xl font-serif font-bold text-foreground">
                    {voice.name}
                  </h3>
                  <p className="text-sm text-muted-foreground font-mono">
                    {voice.language} • {voice.accent}
                  </p>
                </div>
                <span className="text-xs bg-secondary text-foreground px-2 py-1 rounded font-mono">
                  {voice.type === 'default' ? 'Default' : 'Custom'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider">
                Gender: {voice.gender}
              </p>
            </div>

            {/* Voice Parameters */}
            <div className="bg-background rounded-lg p-4 mb-4 space-y-3">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-mono text-muted-foreground uppercase">Speed</span>
                  <span className="text-sm font-mono text-foreground">{voice.speed.toFixed(2)}x</span>
                </div>
                <div className="w-full bg-border rounded-full h-1">
                  <div
                    className="bg-accent h-1 rounded-full transition-all"
                    style={{ width: `${voice.speed * 50}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-mono text-muted-foreground uppercase">Pitch</span>
                  <span className="text-sm font-mono text-foreground">{voice.pitch.toFixed(2)}</span>
                </div>
                <div className="w-full bg-border rounded-full h-1">
                  <div
                    className="bg-accent h-1 rounded-full transition-all"
                    style={{ width: `${voice.pitch * 50}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                onClick={() => setPlayingId(playingId === voice.id ? null : voice.id)}
                variant="outline"
                className="flex-1"
              >
                <Play size={16} className="mr-2" />
                {playingId === voice.id ? 'Stop' : 'Listen'}
              </Button>
              {voice.type === 'custom' && (
                <>
                  <Button variant="outline" size="icon">
                    <Copy size={16} />
                  </Button>
                  <Button variant="outline" size="icon" className="hover:border-red-500 hover:text-red-600">
                    <Trash2 size={16} />
                  </Button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
