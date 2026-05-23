'use client'

import { Button } from '@/components/ui/button'
import { Plus, Save } from 'lucide-react'

export default function AgentBuilderPage() {
  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Agent Builder
          </h1>
          <p className="text-muted-foreground font-mono">
            Visual flow editor for creating voice agent logic
          </p>
        </div>
        <div className="flex gap-4">
          <Button variant="outline">
            Preview Agent
          </Button>
          <Button className="bg-accent hover:bg-accent/90">
            <Save size={18} className="mr-2" />
            Save Agent
          </Button>
        </div>
      </div>

      {/* Canvas Area */}
      <div className="bg-card border border-border rounded-lg p-8 min-h-[600px] flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4 opacity-10">▨</div>
          <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
            Visual Flow Editor
          </h2>
          <p className="text-muted-foreground font-mono mb-6 max-w-md">
            Drag and drop nodes to build your agent's conversation flow. This is where you define decision trees, prompts, and responses.
          </p>
          <Button className="bg-accent hover:bg-accent/90">
            <Plus size={18} className="mr-2" />
            Add Node
          </Button>
        </div>
      </div>

      {/* Sidebar would go here for node properties */}
    </div>
  )
}
