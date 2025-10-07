"use client"

import React from "react"
import MorphingBlob from "@/components/ui/MorphingBlob"
import useParallax from "@/components/hooks/useParallax"

export default function ParallaxBlob() {
  const { ref } = useParallax(0.18)
  return (
    <div ref={ref as any} className="pointer-events-none absolute right-8 top-8 opacity-60 hidden md:block w-48 h-48">
      <MorphingBlob className="w-full h-full" />
    </div>
  )
}
