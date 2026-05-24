'use client'

export default function AuditLogsPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Audit Logs
        </h1>
        <p className="text-muted-foreground font-mono">
          Track all account activities and changes
        </p>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-background border-b border-border">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Timestamp</th>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Event</th>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">User</th>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[
                { time: '2024-01-20 14:32', event: 'Agent Created', user: 'admin@example.com', details: 'New Support Agent' },
                { time: '2024-01-20 12:15', event: 'Campaign Started', user: 'admin@example.com', details: 'Q4 Retention' },
                { time: '2024-01-20 10:00', event: 'API Key Created', user: 'admin@example.com', details: 'Production Key' },
              ].map((log, i) => (
                <tr key={i} className="hover:bg-background/50 transition-colors">
                  <td className="px-6 py-4 text-sm font-mono text-foreground">{log.time}</td>
                  <td className="px-6 py-4 text-sm font-serif font-semibold text-foreground">{log.event}</td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{log.user}</td>
                  <td className="px-6 py-4 text-sm text-foreground">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
