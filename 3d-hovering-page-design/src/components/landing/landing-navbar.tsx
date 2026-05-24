'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export function LandingNavbar() {
  const [isAtTop, setIsAtTop] = useState(true)
  const [isHovered, setIsHovered] = useState(false)
  const [isMouseNearTop, setIsMouseNearTop] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsAtTop(window.scrollY < 50)
    }

    const handleMouseMove = (e: MouseEvent) => {
      // Trigger when mouse is within 50px of the top edge of screen
      setIsMouseNearTop(e.clientY < 50)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('mousemove', handleMouseMove)

    // Run once initially
    handleScroll()

    return () => {
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [])

  const isVisible = isAtTop || isHovered || isMouseNearTop

  return (
    <nav
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ease-out ${
        isVisible
          ? 'translate-y-0 opacity-100 pointer-events-auto'
          : '-translate-y-full opacity-0 pointer-events-none'
      } ${
        isAtTop
          ? 'bg-stone-100/80 backdrop-blur-md border-b border-stone-200/30 py-2'
          : 'bg-stone-100/70 backdrop-blur-lg border-b border-stone-200/40 shadow-xs py-1'
      }`}
    >
      <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-stone-900 rounded-lg flex items-center justify-center">
            <span className="text-stone-100 font-serif font-bold text-sm">V</span>
          </div>
          <span className="font-serif font-bold text-lg text-stone-900">VoiceFlow</span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          <Link href="/" className="text-base text-stone-700 hover:text-stone-900 transition-colors font-serif">
            Home
          </Link>
          <Link href="#features" className="text-base text-stone-700 hover:text-stone-900 transition-colors font-serif">
            Features
          </Link>
          <Link href="#pricing" className="text-base text-stone-700 hover:text-stone-900 transition-colors font-serif">
            Pricing
          </Link>
          <Link href="#contact" className="text-base text-stone-700 hover:text-stone-900 transition-colors font-serif">
            Contact
          </Link>
        </div>

        <div className="flex items-center gap-6">
          <Link href="/login" className="hidden sm:inline text-base font-serif text-stone-700 hover:text-stone-900 transition-colors">
            Sign In
          </Link>
          <Link href="/register">
            <Button className="bg-stone-900 hover:bg-stone-800 text-white font-serif rounded-lg px-6 py-2.5 text-base">
              Get Started
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  )
}
