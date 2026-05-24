'use client'

import { Button } from '@/components/ui/button'
import { Plus, Download } from 'lucide-react'

export default function ReportsPage() {
  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Reports
          </h1>
          <p className="text-muted-foreground font-mono">
            Generate and view call reports
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Generate Report
        </Button>
      </div>

      <div className="space-y-4">
        {[
          { name: 'Monthly Summary - January 2024', date: '2024-01-31', calls: 12450 },
          { name: 'Campaign Performance Report', date: '2024-01-20', calls: 3456 },
          { name: 'Voice Quality Analysis', date: '2024-01-15', calls: 5678 },
        ].map((report, i) => (
          <div key={i} className="bg-card border border-border rounded-lg p-6 flex items-center justify-between">
            <div>
              <h3 className="font-serif font-bold text-foreground">{report.name}</h3>
              <p className="text-sm text-muted-foreground font-mono">{report.date} • {report.calls} calls</p>
            </div>
            <Button variant="outline">
              <Download size={16} className="mr-2" />
              Download
            </Button>
          </div>
        ))}
      </div>
    </div>
  )
}
