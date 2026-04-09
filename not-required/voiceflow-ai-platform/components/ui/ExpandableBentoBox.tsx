"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"

export default function ExpandableBentoBox({ title, children }: { title: string, children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <motion.div layout className="border rounded-xl bg-card overflow-hidden" onClick={() => setOpen(o => !o)}>
      <div className="p-4 flex items-center justify-between cursor-pointer">
        <div className="font-semibold">{title}</div>
        <div className="text-sm text-muted-foreground">{open ? 'Close' : 'Open'}</div>
      </div>
      {open && (
        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="p-4 border-t">
          {children}
        </motion.div>
      )}
    </motion.div>
  )
}
