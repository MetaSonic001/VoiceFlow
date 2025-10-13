"use client"

import React from "react"
import { Header } from "@/components/Header"
import { Hero } from "@/components/Hero"
import { Features } from "@/components/Features"
import { Pricing } from "@/components/Pricing"
import { useRouter } from "next/navigation"
import { useClerk } from '@clerk/nextjs'

export default function HomePage() {
  // Clerk handles sign-in / sign-up UI. No local fallback modal is used.
  const router = useRouter()
  const clerk = useClerk() as any

  const handleGetStarted = () => {
    // Prefer opening Clerk sign-up if available, fallback to local AuthModal
    if (clerk?.openSignUp) {
      clerk.openSignUp()
      return
    }
    console.warn('Clerk not available: cannot open sign-up. Redirecting to onboarding as fallback.')
    router.push('/onboarding')
  }

  const handleSignIn = () => {
    // Prefer opening Clerk sign-in if available, fallback to local AuthModal
    if (clerk?.openSignIn) {
      clerk.openSignIn()
      return
    }
    console.warn('Clerk not available: cannot open sign-in. Redirecting to dashboard as fallback.')
    router.push('/dashboard')
  }

  return (
    <div className="min-h-screen bg-white">
      <Header
        onLoginClick={handleSignIn}
        onSignupClick={handleGetStarted}
      />
      
      <Hero onGetStarted={handleGetStarted} />
      <Features />
      <Pricing onGetStarted={handleGetStarted} />

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4">
            <h3 className="text-2xl font-bold">VoiceFlow AI</h3>
            <p className="text-gray-400">
              Build, deploy, and manage intelligent voice agents in minutes
            </p>
            <div className="pt-8 border-t border-gray-800">
              <p className="text-gray-500">
                © 2024 VoiceFlow AI. All rights reserved.
              </p>
            </div>
          </div>
        </div>
      </footer>

      {/* AuthModal removed: Clerk manages sign-in/sign-up UI */}
    </div>
  )
}