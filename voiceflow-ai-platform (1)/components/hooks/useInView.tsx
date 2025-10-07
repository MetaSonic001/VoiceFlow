"use client"

import { useEffect, useRef, useState } from "react"

export default function useInView<T extends HTMLElement>(options?: IntersectionObserverInit) {
  const ref = useRef<T | null>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) setInView(true)
      })
    }, options)
    obs.observe(el)
    return () => obs.disconnect()
  }, [ref.current])

  return { ref, inView }
}
