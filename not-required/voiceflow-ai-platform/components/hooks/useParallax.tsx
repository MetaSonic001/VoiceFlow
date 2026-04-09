"use client"

import { useEffect, useRef } from "react"

export default function useParallax(amount = 0.2) {
  const ref = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const onScroll = () => {
      const rect = el.getBoundingClientRect()
      const windowHeight = window.innerHeight
      const pct = (rect.top + rect.height) / (windowHeight + rect.height)
      const translate = (pct - 0.5) * amount * 100
      el.style.transform = `translateY(${translate}px)`
    }

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [ref.current])

  return { ref }
}
