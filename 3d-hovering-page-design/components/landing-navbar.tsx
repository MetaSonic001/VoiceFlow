import Link from 'next/link'
import { Button } from '@/components/ui/button'

export function LandingNavbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm border-b border-border">
      <div className="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
            <span className="text-background font-serif font-bold text-sm">V</span>
          </div>
          <span className="font-serif font-bold text-lg text-foreground">VoiceFlow</span>
        </Link>

        {/* Navigation Links */}
        <div className="hidden md:flex items-center gap-8">
          <Link href="/" className="text-sm text-foreground hover:text-accent transition-colors font-mono">
            Home
          </Link>
          <Link href="#features" className="text-sm text-foreground hover:text-accent transition-colors font-mono">
            Features
          </Link>
          <Link href="#pricing" className="text-sm text-foreground hover:text-accent transition-colors font-mono">
            Pricing
          </Link>
          <Link href="#contact" className="text-sm text-foreground hover:text-accent transition-colors font-mono">
            Contact
          </Link>
        </div>

        {/* CTA Button */}
        <Link href="/dashboard">
          <Button className="bg-accent hover:bg-accent/90 text-accent-foreground">
            Get Started
          </Button>
        </Link>
      </div>
    </nav>
  )
}
