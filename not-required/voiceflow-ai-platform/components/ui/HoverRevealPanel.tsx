"use client"

import React from "react"

export default function HoverRevealPanel({ preview, details, className = "" }: { preview: React.ReactNode, details: React.ReactNode, className?: string }) {
  return (
    <div className={"relative overflow-hidden rounded-xl border bg-card " + className}>
      <div className="p-4">
        {preview}
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none">
        <div className="p-6 text-white pointer-events-auto">
          {details}
        </div>
      </div>
    </div>
  )
}
