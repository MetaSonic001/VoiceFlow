'use client'

import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'

export default function SIPTrunkingPage() {
  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            SIP Trunking
          </h1>
          <p className="text-muted-foreground font-mono">
            Configure and manage SIP trunk connections
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Add SIP Trunk
        </Button>
      </div>

      <div className="bg-card border border-border rounded-lg p-8">
        <div className="text-center">
          <div className="text-5xl mb-4 opacity-10">⚙</div>
          <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
            SIP Configuration
          </h2>
          <p className="text-muted-foreground font-mono max-w-md mx-auto">
            Connect your VoiceFlow system to external SIP providers for advanced call routing and integration.
          </p>
        </div>
      </div>
    </div>
  )
}
