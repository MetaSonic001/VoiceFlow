"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Mic, MicOff } from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Message {
  id: string
  speaker: "user" | "agent"
  message: string
  timestamp: string
  chunks_used?: string[]
}

interface ChatInterfaceProps {
  agentId?: string
  sessionId?: string
  title?: string
  className?: string
}

export function ChatInterface({ agentId, sessionId, title = "Test Your Agent", className }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState(sessionId || "")
  const [isRecording, setIsRecording] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Generate session ID if not provided
    if (!currentSessionId) {
      setCurrentSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
    }
  }, [currentSessionId])

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  const sendMessage = async (message: string) => {
    if (!message.trim() || !currentSessionId) return

    const userMessage: Message = {
      id: `user_${Date.now()}`,
      speaker: "user",
      message: message.trim(),
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInputMessage("")
    setLoading(true)

    try {
      const response = await apiClient.sendMessage(currentSessionId, message.trim())

      const agentMessage: Message = {
        id: `agent_${Date.now()}`,
        speaker: "agent",
        message: response.response,
        timestamp: new Date().toISOString(),
        chunks_used: response.chunks_used,
      }

      setMessages((prev) => [...prev, agentMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        speaker: "agent",
        message: `Sorry, I encountered an error: ${error.message}`,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(inputMessage)
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const audioChunks: BlobPart[] = []

      recorder.ondataavailable = (event) => {
        audioChunks.push(event.data)
      }

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" })
        const audioFile = new File([audioBlob], "recording.wav", { type: "audio/wav" })

        setLoading(true)
        try {
          const response = await apiClient.sendAudioMessage(currentSessionId, audioFile)

          if (response.transcript) {
            const userMessage: Message = {
              id: `user_audio_${Date.now()}`,
              speaker: "user",
              message: `🎤 ${response.transcript}`,
              timestamp: new Date().toISOString(),
            }
            setMessages((prev) => [...prev, userMessage])
          }

          const agentMessage: Message = {
            id: `agent_audio_${Date.now()}`,
            speaker: "agent",
            message: response.response,
            timestamp: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, agentMessage])
        } catch (error: any) {
          const errorMessage: Message = {
            id: `error_audio_${Date.now()}`,
            speaker: "agent",
            message: `Sorry, I couldn't process your audio: ${error.message}`,
            timestamp: new Date().toISOString(),
          }
          setMessages((prev) => [...prev, errorMessage])
        } finally {
          setLoading(false)
        }

        // Clean up
        stream.getTracks().forEach((track) => track.stop())
      }

      setMediaRecorder(recorder)
      recorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error("Error starting recording:", error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop()
      setIsRecording(false)
      setMediaRecorder(null)
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          {title}
          {currentSessionId && (
            <span className="text-xs text-muted-foreground font-mono">Session: {currentSessionId.slice(-8)}</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ScrollArea className="h-96 w-full border rounded-md p-4" ref={scrollAreaRef}>
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground py-8">Start a conversation with your AI agent</div>
            )}
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.speaker === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 ${
                    message.speaker === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  <p className="text-sm">{message.message}</p>
                  {message.chunks_used && message.chunks_used.length > 0 && (
                    <div className="mt-2 text-xs opacity-70">
                      <details>
                        <summary className="cursor-pointer">Debug: Chunks used ({message.chunks_used.length})</summary>
                        <div className="mt-1 space-y-1">
                          {message.chunks_used.map((chunk, index) => (
                            <div key={index} className="bg-black/10 rounded p-1 text-xs">
                              {chunk.substring(0, 100)}...
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}
                  <div className="text-xs opacity-50 mt-1">{new Date(message.timestamp).toLocaleTimeString()}</div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-muted text-muted-foreground rounded-lg px-3 py-2">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                    <span className="text-sm">Agent is thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <form onSubmit={handleSubmit} className="flex space-x-2">
          <Input
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your message..."
            disabled={loading}
            className="flex-1"
          />
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={isRecording ? stopRecording : startRecording}
            disabled={loading}
            className={isRecording ? "bg-red-100 text-red-600" : ""}
          >
            {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </Button>
          <Button type="submit" disabled={loading || !inputMessage.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
