import { ReactNode } from 'react'
import { motion } from 'framer-motion'

export const MOTION = {
  duration: 0.36,
  ease: ['easeOut'] as any,
}

export const containerVariants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      staggerChildren: 0.06,
      when: 'beforeChildren',
      duration: MOTION.duration,
      ease: MOTION.ease,
    },
  },
  exit: { opacity: 0, y: -8, transition: { duration: MOTION.duration, ease: MOTION.ease } },
}

export const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: MOTION.ease } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.28, ease: MOTION.ease } },
}

export default function MotionWrapper({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      initial="hidden"
      animate="show"
      exit="exit"
      variants={containerVariants}
      className={className}
    >
      {children}
    </motion.div>
  )
}
