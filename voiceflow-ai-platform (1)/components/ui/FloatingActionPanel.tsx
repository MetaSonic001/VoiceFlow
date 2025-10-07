"use client"

import React from "react"

export default function FloatingActionPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="fixed right-6 bottom-6 z-50">
      <div className="bg-card border rounded-full p-3 shadow-xl">
        {children}
      </div>
    </div>
  )
}
