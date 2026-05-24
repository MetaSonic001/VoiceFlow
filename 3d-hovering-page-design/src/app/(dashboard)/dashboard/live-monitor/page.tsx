'use client'

export default function LiveMonitorPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Live Call Monitor
        </h1>
        <p className="text-muted-foreground font-mono">
          Monitor active calls in real-time
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg p-8">
        <div className="text-center">
          <div className="text-5xl mb-4 opacity-10">📞</div>
          <h2 className="text-2xl font-serif font-bold text-foreground mb-2">
            No Active Calls
          </h2>
          <p className="text-muted-foreground font-mono max-w-md mx-auto">
            Active calls will appear here when agents are handling incoming or outgoing calls.
          </p>
        </div>
      </div>
    </div>
  )
}
