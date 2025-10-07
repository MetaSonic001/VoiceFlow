"use client"

import React from "react"

export default function Timeline({ steps }: { steps: { title: string; subtitle?: string; done?: boolean }[] }) {
  return (
    <div className="space-y-6">
      {steps.map((s, i) => (
        <div key={i} className="flex items-start space-x-4">
          <div className={`w-3 h-3 rounded-full mt-1 ${s.done ? 'bg-primary' : 'bg-muted'}`}></div>
          <div>
            <div className="font-semibold">{s.title}</div>
            {s.subtitle && <div className="text-sm text-muted-foreground">{s.subtitle}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}
