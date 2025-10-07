"use client"

import React from 'react'
import { motion } from 'framer-motion'
import FeatureCard from './FeatureCard'
import { containerVariants, itemVariants } from '@/components/ui/MotionWrapper'

export default function FeatureGrid({ items }: { items: { title: string; description: string; icon?: React.ReactNode }[] }) {
  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {items.map((it, i) => (
        <motion.div key={i} variants={itemVariants} className="p-1">
          <FeatureCard title={it.title} icon={it.icon}>{it.description}</FeatureCard>
        </motion.div>
      ))}
    </motion.div>
  )
}
