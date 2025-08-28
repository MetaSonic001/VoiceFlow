"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Phone, Play, Mic } from "lucide-react"
import { ChatInterface } from "@/components/chat-interface"

interface TestingSandboxProps {
  onComplete: (data: any) => void
}

export function TestingSandbox({ onComplete }: TestingSandboxProps) {
  const [isCallActive, setIsCallActive] = useState(false)
  const [chatTested, setChatTested] = useState(false)

  const startPhoneTest = () => {
    setIsCallActive(true)
    // Simulate call ending after 5 seconds
    setTimeout(() => setIsCallActive(false), 5000)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onComplete({ testing: { chatTested, phoneTested: true } })
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Play className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Test your AI agent</h2>
        <p className="text-muted-foreground">
          Try out your agent before going live. Test both chat and phone interactions to ensure everything works
          perfectly.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Chat Testing */}
        <ChatInterface title="Chat Test" className="h-full" sessionId={`test_${Date.now()}`} />

        {/* Phone Testing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Phone className="w-5 h-5" />
              <span>Phone Test</span>
            </CardTitle>
            <CardDescription>Test your agent's voice interactions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="h-96 border border-border rounded-lg p-4 flex flex-col items-center justify-center space-y-4">
              {!isCallActive ? (
                <>
                  <div className="text-center">
                    <Phone className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                    <p className="text-sm text-muted-foreground">Click to start a test call</p>
                    <p className="text-xs text-muted-foreground mt-1">Test number: +1 (555) 123-4567</p>
                  </div>
                  <Button onClick={startPhoneTest} variant="outline">
                    <Mic className="w-4 h-4 mr-2" />
                    Start Test Call
                  </Button>
                </>
              ) : (
                <div className="text-center">
                  <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
                    <Phone className="w-8 h-8 text-white" />
                  </div>
                  <Badge variant="secondary" className="bg-green-100 text-green-800">
                    Call Active
                  </Badge>
                  <p className="text-sm text-muted-foreground mt-2">Testing voice interaction...</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Testing Checklist</CardTitle>
            <CardDescription>Make sure everything works before going live</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className={`w-4 h-4 rounded-full ${chatTested ? "bg-green-500" : "bg-muted"}`} />
              <span className="text-sm">Chat responses are working correctly</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 rounded-full bg-green-500" />
              <span className="text-sm">Phone number is configured</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 rounded-full bg-green-500" />
              <span className="text-sm">Knowledge base is loaded</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 rounded-full bg-green-500" />
              <span className="text-sm">Voice and personality are set</span>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" className="w-full mt-6">
          Everything looks good - Go Live!
        </Button>
      </form>
    </div>
  )
}
