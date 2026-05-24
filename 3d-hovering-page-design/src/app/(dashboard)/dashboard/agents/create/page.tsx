'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ArrowRight, ArrowLeft } from 'lucide-react'

export default function CreateAgentPage() {
  const [step, setStep] = useState(1)

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Create New Agent
        </h1>
        <p className="text-muted-foreground font-mono">
          Step {step} of 4: Agent Configuration
        </p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8 flex gap-2">
        {[1, 2, 3, 4].map((s) => (
          <div
            key={s}
            className={`flex-1 h-2 rounded-full transition-colors ${
              s <= step ? 'bg-accent' : 'bg-border'
            }`}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          <div className="bg-card border border-border rounded-lg p-8">
            {step === 1 && (
              <div className="space-y-6">
                <h2 className="text-2xl font-serif font-bold text-foreground">Basic Information</h2>
                
                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    Agent Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Customer Support Agent"
                    className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>

                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    Description
                  </label>
                  <textarea
                    placeholder="What does this agent do?"
                    className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-accent min-h-24"
                  />
                </div>

                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    Agent Type
                  </label>
                  <select className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-accent">
                    <option>Inbound (Incoming Calls)</option>
                    <option>Outbound (Outgoing Calls)</option>
                    <option>Hybrid (Both)</option>
                  </select>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h2 className="text-2xl font-serif font-bold text-foreground">Voice Configuration</h2>
                
                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    Select Voice
                  </label>
                  <select className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-accent">
                    <option>Sarah (Female, American)</option>
                    <option>Alex (Male, American)</option>
                    <option>Emma (Female, British)</option>
                    <option>James (Male, American)</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    Speaking Speed
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.1"
                    defaultValue="1"
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground mt-2">1.0x (Normal speed)</p>
                </div>

                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    System Prompt
                  </label>
                  <textarea
                    placeholder="Define the agent's behavior and personality..."
                    className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-accent min-h-24"
                  />
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6">
                <h2 className="text-2xl font-serif font-bold text-foreground">Intelligence Settings</h2>
                
                <div>
                  <label className="text-sm font-mono text-muted-foreground uppercase mb-2 block">
                    Temperature (Creativity)
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
                    Max Response Length
                  </label>
                  <input
                    type="number"
                    defaultValue="500"
                    className="w-full bg-background border border-border rounded-lg px-4 py-3 text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>

                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" defaultChecked className="w-4 h-4" />
                    <span className="text-sm font-mono text-foreground">Enable conversation history</span>
                  </label>
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-6">
                <h2 className="text-2xl font-serif font-bold text-foreground">Review & Create</h2>
                
                <div className="bg-background rounded-lg p-6 space-y-4">
                  <div>
                    <p className="text-xs font-mono text-muted-foreground uppercase mb-1">Agent Name</p>
                    <p className="font-serif text-foreground">Customer Support Agent</p>
                  </div>
                  <div>
                    <p className="text-xs font-mono text-muted-foreground uppercase mb-1">Voice</p>
                    <p className="font-serif text-foreground">Sarah (Female, American)</p>
                  </div>
                  <div>
                    <p className="text-xs font-mono text-muted-foreground uppercase mb-1">Agent Type</p>
                    <p className="font-serif text-foreground">Inbound (Incoming Calls)</p>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground font-mono">
                  Review your configuration and click &quot;Create Agent&quot; to deploy your new AI voice agent.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="font-serif font-bold text-foreground mb-4">Steps</h3>
            <ul className="space-y-2 text-sm">
              {[
                { num: 1, label: 'Basic Info' },
                { num: 2, label: 'Voice' },
                { num: 3, label: 'Intelligence' },
                { num: 4, label: 'Review' },
              ].map((s) => (
                <li key={s.num}>
                  <button
                    onClick={() => setStep(s.num)}
                    className={`flex items-center gap-3 w-full px-3 py-2 rounded transition-colors ${
                      step === s.num
                        ? 'bg-accent text-accent-foreground font-semibold'
                        : 'text-foreground hover:bg-background'
                    }`}
                  >
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-mono ${
                      step === s.num ? 'bg-accent-foreground text-accent' : 'border border-border'
                    }`}>
                      {s.num}
                    </span>
                    {s.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="mt-8 flex gap-4 justify-between">
        <Button
          variant="outline"
          onClick={() => setStep(Math.max(1, step - 1))}
          disabled={step === 1}
        >
          <ArrowLeft size={16} className="mr-2" />
          Previous
        </Button>
        
        {step < 4 ? (
          <Button
            className="bg-accent hover:bg-accent/90"
            onClick={() => setStep(Math.min(4, step + 1))}
          >
            Next
            <ArrowRight size={16} className="ml-2" />
          </Button>
        ) : (
          <Button className="bg-accent hover:bg-accent/90">
            Create Agent
          </Button>
        )}
      </div>
    </div>
  )
}
