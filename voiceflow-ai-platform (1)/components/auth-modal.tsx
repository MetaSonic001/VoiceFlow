"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Brain, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { apiClient } from "@/lib/api-client"

interface AuthModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: "login" | "signup"
  onModeChange: (mode: "login" | "signup") => void
}

export function AuthModal({ open, onOpenChange, mode, onModeChange }: AuthModalProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [companyName, setCompanyName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      let response
      if (mode === "login") {
        response = await apiClient.login(email, password)
        router.push("/dashboard")
      } else {
        response = await apiClient.signup(email, password, companyName)
        router.push("/onboarding")
      }

      // Store auth token and session ID
      localStorage.setItem("auth_token", response.token)
      localStorage.setItem("session_id", response.session_id)
      localStorage.setItem("user", JSON.stringify(response.user))

      onOpenChange(false)
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please try again.")
    } finally {
      setLoading(false)
    }
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

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "signup" && (
            <div className="space-y-2">
              <Label htmlFor="company" className="text-sm font-medium">
                Company Name
              </Label>
              <Input
                id="company"
                type="text"
                placeholder="Acme Inc."
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                required
                className="h-11"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-11"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium">
              Password
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="h-11"
            />
          </div>

          {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 p-3 rounded-lg">{error}</div>}

          <Button
            type="submit"
            className="w-full h-11 bg-gradient-to-r from-primary to-accent hover:scale-105 transition-all duration-300"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Please wait...
              </>
            ) : mode === "login" ? (
              "Sign In"
            ) : (
              "Create Account"
            )}
          </Button>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <Separator className="w-full" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">
              {mode === "login" ? "New to VoiceFlow AI?" : "Already have an account?"}
            </span>
          </div>
        </div>

        <Button
          variant="ghost"
          className="w-full h-11 hover:bg-muted/50 transition-colors"
          onClick={() => onModeChange(mode === "login" ? "signup" : "login")}
        >
          {mode === "login" ? "Create an account" : "Sign in instead"}
        </Button>

        <div className="text-center text-xs text-muted-foreground pt-2">
          <div className="flex items-center justify-center space-x-4">
            <span>🔒 256-bit SSL encryption</span>
            <span>🇮🇳 Made in India</span>
            <span>⚡ 5-min setup</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
