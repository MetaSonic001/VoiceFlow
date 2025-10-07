"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { itemVariants, MOTION } from '@/components/ui/MotionWrapper'

export default function FeatureHero({ title, subtitle, onPrimary }: { title: string; subtitle?: string; onPrimary?: () => void }) {
  return (
    <motion.div variants={itemVariants} className="relative max-w-5xl mx-auto text-center py-12 px-4">
      <h2 className="text-3xl md:text-4xl font-extrabold mb-4">{title}</h2>
      {subtitle && <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-6">{subtitle}</p>}
      <div className="flex justify-center">
        <Button size="lg" onClick={onPrimary} className="bg-primary">
          <Play className="w-4 h-4 mr-2" /> Get Started
        </Button>
      </div>
    </motion.div>
  )
}
