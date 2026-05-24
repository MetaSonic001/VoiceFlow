'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Mic, Play, Square, Settings } from 'lucide-react'

export default function VoiceAgentPage() {
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Voice Agent Test Bench
        </h1>
        <p className="text-muted-foreground font-mono">
          Test and debug your voice AI in real-time
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Testing Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Agent Selection */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4">
              Select Agent
            </h2>
            <select className="w-full bg-input border border-border rounded-lg px-4 py-3 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent">
              <option>Customer Support Agent</option>
              <option>Sales Outreach Bot</option>
              <option>Appointment Scheduler</option>
              <option>Survey Assistant</option>
            </select>
          </div>

          {/* Test Input */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4">
              Input Method
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                  Text Input
                </label>
                <textarea
                  placeholder="Enter a message for the voice agent to respond to..."
                  className="w-full bg-input border border-border rounded-lg px-4 py-3 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent min-h-32"
                />
              </div>

              <div className="flex gap-4">
                <Button
                  onClick={() => setIsRecording(!isRecording)}
                  variant="outline"
                  className={isRecording ? 'bg-red-100 border-red-300' : ''}
                >
                  <Mic size={18} className="mr-2" />
                  {isRecording ? 'Stop Recording' : 'Start Recording'}
                </Button>
                <Button variant="outline">
                  <Play size={18} className="mr-2" />
                  Test Voice Input
                </Button>
              </div>
            </div>
          </div>

          {/* Response Output */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4">
              Agent Response
            </h2>
            <div className="bg-background border border-border rounded-lg p-4 font-mono text-sm text-foreground min-h-40">
              <p className="text-muted-foreground">Response will appear here...</p>
            </div>
            <div className="mt-4 flex gap-3">
              <Button
                onClick={() => setIsPlaying(!isPlaying)}
                variant="outline"
              >
                {isPlaying ? <Square size={18} /> : <Play size={18} />}
                <span className="ml-2">{isPlaying ? 'Stop' : 'Play'} Response</span>
              </Button>
              <Button variant="outline">
                Copy Response
              </Button>
            </div>
          </div>
        </div>

        {/* Sidebar Config */}
        <div className="space-y-6">
          {/* Agent Settings */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4 flex items-center">
              <Settings size={18} className="mr-2" />
              Settings
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                  Voice
                </label>
                <select className="w-full bg-input border border-border rounded-lg px-3 py-2 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent">
                  <option>Sarah (Default)</option>
                  <option>Alex</option>
                  <option>James</option>
                  <option>Emma</option>
                  <option>David</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                  Temperature
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  defaultValue="0.7"
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground mt-2">0.7 (Balanced)</p>
              </div>

              <div>
                <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                  Max Tokens
                </label>
                <input
                  type="number"
                  defaultValue="500"
                  className="w-full bg-input border border-border rounded-lg px-3 py-2 text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>
            </div>
          </div>

          {/* Test History */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-serif font-bold text-foreground mb-4">
              Test History
            </h2>
            <div className="space-y-3">
              <div className="bg-background rounded p-3 text-xs font-mono">
                <p className="text-muted-foreground mb-1">2 minutes ago</p>
                <p className="text-foreground">Test #1234</p>
              </div>
              <div className="bg-background rounded p-3 text-xs font-mono">
                <p className="text-muted-foreground mb-1">15 minutes ago</p>
                <p className="text-foreground">Test #1233</p>
              </div>
              <div className="bg-background rounded p-3 text-xs font-mono">
                <p className="text-muted-foreground mb-1">1 hour ago</p>
                <p className="text-foreground">Test #1232</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
