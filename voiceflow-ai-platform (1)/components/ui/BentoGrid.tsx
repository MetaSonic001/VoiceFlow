"use client"

import React from "react"
import { motion } from "framer-motion"
import FeatureCard from "@/components/ui/FeatureCard"
import { containerVariants, itemVariants } from "@/components/ui/MotionWrapper"
import Tilt3D from "@/components/ui/Tilt3D"
import useInView from "@/components/hooks/useInView"

type Item = {
  icon: any
  title: string
  description: string
  color?: string
}

export default function BentoGrid({ items }: { items: Item[] }) {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.12 })

  return (
    <motion.div
      ref={ref}
      variants={containerVariants}
      initial="hidden"
      animate={inView ? "show" : "hidden"}
      className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      {items.map((it, i) => (
        <motion.div key={i} variants={itemVariants} className="transform-gpu">
          <Tilt3D>
            <FeatureCard title={it.title} icon={<it.icon className={`w-6 h-6 text-${it.color ?? "primary"}-500`} />}>
              {it.description}
            </FeatureCard>
          </Tilt3D>
        </motion.div>
      ))}
    </motion.div>
  )
}
