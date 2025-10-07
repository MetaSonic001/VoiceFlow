"use client"

import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MOTION } from '@/components/ui/MotionWrapper'
import { Quote } from 'lucide-react'

interface Testimonial { name: string; company: string; role?: string; content: string }

export default function TestimonialCarousel({ items = [] as Testimonial[] }: { items?: Testimonial[] }) {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setIndex((i) => (i + 1) % items.length), 4500)
    return () => clearInterval(t)
  }, [items.length])

  if (!items || items.length === 0) return null

  return (
    <div className="max-w-3xl mx-auto">
      <AnimatePresence mode="wait">
        <motion.blockquote
          key={index}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: MOTION.duration + 0.08, ease: MOTION.ease }}
          className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-lg border border-gray-100"
        >
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-50 rounded-full">
              <Quote className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-gray-700 dark:text-gray-200 leading-relaxed">{items[index].content}</p>
              <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                <strong className="text-gray-900 dark:text-gray-100">{items[index].name}</strong>
                {', '}
                <span>{items[index].company}</span>
              </div>
            </div>
          </div>
        </motion.blockquote>
      </AnimatePresence>
    </div>
  )
}
