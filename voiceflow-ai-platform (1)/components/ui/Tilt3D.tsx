"use client"

import React, { useRef } from "react"

export default function Tilt3D({ children, className = "", max = 12 }: { children: React.ReactNode, className?: string, max?: number }) {
  const ref = useRef<HTMLDivElement | null>(null)

  return (
    <div
      ref={ref}
      className={"will-change-transform transition-transform duration-200 transform-gpu " + className}
      onMouseMove={(e) => {
        const el = ref.current
        if (!el) return
        const rect = el.getBoundingClientRect()
        const x = (e.clientX - rect.left) / rect.width
        const y = (e.clientY - rect.top) / rect.height
        const rotY = (x - 0.5) * max
        const rotX = (0.5 - y) * max
        el.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(0)`
      }}
      onMouseLeave={() => {
        const el = ref.current
        if (!el) return
        el.style.transform = ''
      }}
    >
      {children}
    </div>
  )
}
