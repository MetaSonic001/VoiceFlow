"use client"

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Sparkles } from 'lucide-react'

export default function PromoBanner({ children }: { children?: React.ReactNode }) {
  return (
    <div className="w-full flex justify-center">
      <Badge variant="secondary" className="mb-6 px-4 py-2 text-sm font-semibold bg-gradient-to-r from-primary/10 to-accent/10 border-primary/20">
        <Sparkles className="w-4 h-4 mr-2" />
        {children ?? 'Next-Generation AI Platform • Trusted by 10,000+ Businesses'}
      </Badge>
    </div>
  )
}
