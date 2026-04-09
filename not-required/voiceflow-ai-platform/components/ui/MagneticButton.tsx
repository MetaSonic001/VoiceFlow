"use client"

import React from "react"

export default function MagneticButton({ children, className = "", onClick }: { children: React.ReactNode, className?: string, onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className={"relative overflow-hidden rounded-full px-6 py-3 font-semibold transition-transform transform-gpu hover:scale-105 " + className}
      onMouseMove={(e) => {
        const target = e.currentTarget as HTMLElement
        const rect = target.getBoundingClientRect()
        const x = e.clientX - rect.left - rect.width / 2
        const y = e.clientY - rect.top - rect.height / 2
        target.style.transform = `translate3d(${x * 0.03}px, ${y * 0.03}px, 0) scale(1.02)`
      }}
      onMouseLeave={(e) => {
        const target = e.currentTarget as HTMLElement
        target.style.transform = ''
      }}
    >
      {children}
    </button>
  )
}
