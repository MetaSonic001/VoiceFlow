"use client"

import type React from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Brain } from "lucide-react"
import { useRouter } from 'next/navigation'

interface AuthModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: "login" | "signup"
  onModeChange: (mode: "login" | "signup") => void
}

export function AuthModal({ open, onOpenChange, mode }: AuthModalProps) {
  const router = useRouter()

  const handleAuth = () => {
    onOpenChange(false)
    router.push(mode === 'signup' ? '/onboarding' : '/dashboard')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-primary to-accent rounded-xl flex items-center justify-center animate-glow">
              <Brain className="w-6 h-6 text-white" />
            </div>
          </div>
          <DialogTitle className="text-2xl font-bold">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </DialogTitle>
          <DialogDescription className="text-base">
            {mode === "login" ? "Sign in to your VoiceFlow AI account" : "Start building AI agents in minutes"}
          </DialogDescription>
        </DialogHeader>

        <Button onClick={handleAuth} className="w-full h-11">
          {mode === "login" ? "Sign In" : "Sign Up"}
        </Button>
      </DialogContent>
    </Dialog>
  )
}

