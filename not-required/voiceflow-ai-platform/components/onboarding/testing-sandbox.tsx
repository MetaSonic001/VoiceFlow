"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Phone, Play, MessageSquare, CheckCircle, Circle, Sparkles, ArrowRight } from "lucide-react"
import { ChatInterface } from "@/components/chat-interface"

interface TestingSandboxProps {
  onComplete: (data: any) => void
  agentId?: string
  agentName?: string
}

export function TestingSandbox({ onComplete, agentId, agentName }: TestingSandboxProps) {
  const [chatTested, setChatTested] = useState(false)
  const [firstResponseReceived, setFirstResponseReceived] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onComplete({ testing: { chatTested, phoneTested: false } })
  }

  // Listen for first successful agent response to mark chat as tested
  const handleChatMessage = useCallback(() => {
    if (!firstResponseReceived) {
      setFirstResponseReceived(true)
      setChatTested(true)
    }
  }, [firstResponseReceived])

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Sparkles className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">See your agent in action</h2>
        <p className="text-muted-foreground max-w-xl mx-auto">
          {agentName ? (
            <>Ask <strong>{agentName}</strong> a question about your business. It will answer using the knowledge you uploaded.</>
          ) : (
            <>Ask your agent a question about your business. It will answer using the knowledge you uploaded.</>
          )}
        </p>
      </div>

      {/* Suggested prompts */}
      {!chatTested && (
        <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">Try asking something like:</p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary" className="cursor-default">"What services do you offer?"</Badge>
            <Badge variant="secondary" className="cursor-default">"Tell me about your company"</Badge>
            <Badge variant="secondary" className="cursor-default">"How can you help me?"</Badge>
          </div>
        </div>
      )}

      {/* Chat panel — full width, this is the hero moment */}
      <div className="border rounded-lg overflow-hidden" style={{ minHeight: 420 }}>
        <ChatInterface
          title={agentName ? `Chat with ${agentName}` : "Chat with your agent"}
          className="h-full"
          agentId={agentId}
          sessionId={`onboarding_test_${agentId || 'default'}`}
          onAgentResponse={handleChatMessage}
        />
      </div>

      {/* Success state */}
      {chatTested && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
          <div>
            <p className="font-medium text-green-800 dark:text-green-200">Your agent is working!</p>
            <p className="text-sm text-green-700 dark:text-green-300">
              It answered using your uploaded knowledge. You can keep testing or proceed to deployment.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Testing Checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center space-x-2">
              {chatTested ? (
                <CheckCircle className="w-4 h-4 text-green-500" />
              ) : (
                <Circle className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm">Agent responded to a chat message using your knowledge</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm">Knowledge base uploaded</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm">Voice and personality configured</span>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" className="w-full mt-6" size="lg">
          {chatTested ? (
            <>
              Everything looks great — Deploy!
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          ) : (
            <>
              Skip Testing & Deploy
              <ArrowRight className="w-4 h-4 ml-2" />
            </>
          )}
        </Button>
      </form>
    </div>
  )
}
