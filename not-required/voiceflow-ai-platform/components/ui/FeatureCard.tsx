import React, { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { itemVariants, MOTION } from './MotionWrapper'

export default function FeatureCard({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <motion.div
      variants={itemVariants}
      whileHover={{ y: -6, boxShadow: '0px 12px 30px rgba(15, 23, 42, 0.12)' }}
      transition={{ duration: MOTION.duration, ease: MOTION.ease }}
      className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-slate-800 p-6"
    >
      <div className="flex items-center space-x-4 mb-3">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-gradient-to-br from-blue-600 to-purple-600 text-white">
          {icon}
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      </div>
      <div className="text-sm text-gray-600 dark:text-gray-300">{children}</div>
    </motion.div>
  )
}
