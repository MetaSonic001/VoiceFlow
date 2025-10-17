"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Mic, MicOff, Volume2, VolumeX, MessageSquare, Phone } from "lucide-react"

interface Message {
  id: string
  speaker: "user" | "agent"
  message: string
  timestamp: string
  transcript?: string
}

interface VoiceAgentInterfaceProps {}

export function VoiceAgentInterface({}: VoiceAgentInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTranscript, setCurrentTranscript] = useState("")
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null)
  const [sessionId] = useState(`voice_session_${Date.now()}`)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    // Initialize audio context
    const initAudio = async () => {
      try {
        const context = new (window.AudioContext || (window as any).webkitAudioContext)()
        setAudioContext(context)
      } catch (error) {
        console.error('Error initializing audio context:', error)
      }
    }
    initAudio()
  }, [])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      })

      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })

      const audioChunks: BlobPart[] = []

      recorder.ondataavailable = (event) => {
        audioChunks.push(event.data)
      }

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" })
        await processAudio(audioBlob)

        // Clean up
        stream.getTracks().forEach((track) => track.stop())
      }

      setMediaRecorder(recorder)
      recorder.start()
      setIsRecording(true)
      setCurrentTranscript("Listening...")
    } catch (error) {
      console.error("Error starting recording:", error)
      setCurrentTranscript("Error: Could not access microphone")
    }
  }

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop()
      setIsRecording(false)
      setCurrentTranscript("")
      setMediaRecorder(null)
    }
  }

  const processAudio = async (audioBlob: Blob) => {
    try {
      setCurrentTranscript("Processing audio...")

      // Convert blob to file for upload
      const audioFile = new File([audioBlob], "recording.webm", { type: "audio/webm" })

      // Send to backend
      const formData = new FormData()
      formData.append('audio', audioFile)
      formData.append('agentId', 'voice-agent')
      formData.append('sessionId', sessionId)

      const response = await fetch('/api/runner/audio', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      // Add user message with transcript
      const userMessage: Message = {
        id: `user_${Date.now()}`,
        speaker: "user",
        message: data.transcript,
        timestamp: new Date().toISOString(),
        transcript: data.transcript
      }
      setMessages((prev) => [...prev, userMessage])

      // Add agent response
      const agentMessage: Message = {
        id: `agent_${Date.now()}`,
        speaker: "agent",
        message: data.response,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, agentMessage])

      // Play TTS response
      await playTTSResponse(data.response)

      setCurrentTranscript("")
    } catch (error: any) {
      console.error('Error processing audio:', error)
      setCurrentTranscript(`Error: ${error.message}`)
    }
  }

  const playTTSResponse = async (text: string) => {
    try {
      setIsPlaying(true)

      // For now, use Web Speech API as fallback
      // In production, you'd fetch TTS audio from backend
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.rate = 0.9
        utterance.pitch = 1
        utterance.volume = 0.8

        utterance.onend = () => setIsPlaying(false)
        utterance.onerror = () => setIsPlaying(false)

        window.speechSynthesis.speak(utterance)
      } else {
        // Fallback: just mark as complete
        setTimeout(() => setIsPlaying(false), 2000)
      }
    } catch (error) {
      console.error('Error playing TTS:', error)
      setIsPlaying(false)
    }
  }

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Voice Agent
          </h1>
          <p className="text-muted-foreground text-lg">
            Converse naturally with your AI agent using voice or text
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Voice Interface */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Phone className="w-5 h-5" />
                <span>Voice Conversation</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Recording Status */}
              <div className="text-center">
                {isRecording ? (
                  <div className="space-y-4">
                    <div className="w-20 h-20 bg-red-500 rounded-full flex items-center justify-center mx-auto animate-pulse">
                      <Mic className="w-8 h-8 text-white" />
                    </div>
                    <Badge variant="destructive" className="animate-pulse">
                      Recording...
                    </Badge>
                  </div>
                ) : isPlaying ? (
                  <div className="space-y-4">
                    <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto animate-pulse">
                      <Volume2 className="w-8 h-8 text-white" />
                    </div>
                    <Badge variant="secondary" className="bg-green-100 text-green-800">
                      Speaking...
                    </Badge>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="w-20 h-20 bg-slate-200 rounded-full flex items-center justify-center mx-auto">
                      <Mic className="w-8 h-8 text-slate-600" />
                    </div>
                    <Badge variant="outline">
                      Ready to listen
                    </Badge>
                  </div>
                )}
              </div>

              {/* Transcript Display */}
              {currentTranscript && (
                <div className="bg-slate-50 rounded-lg p-4 border">
                  <div className="flex items-center space-x-2 mb-2">
                    <MessageSquare className="w-4 h-4 text-slate-500" />
                    <span className="text-sm font-medium text-slate-700">Live Transcript</span>
                  </div>
                  <p className="text-slate-600">{currentTranscript}</p>
                </div>
              )}

              {/* Voice Controls */}
              <div className="flex justify-center space-x-4">
                <Button
                  onClick={toggleRecording}
                  size="lg"
                  variant={isRecording ? "destructive" : "default"}
                  className="w-32"
                  disabled={isPlaying}
                >
                  {isRecording ? (
                    <>
                      <MicOff className="w-4 h-4 mr-2" />
                      Stop
                    </>
                  ) : (
                    <>
                      <Mic className="w-4 h-4 mr-2" />
                      Talk
                    </>
                  )}
                </Button>

                <Button
                  onClick={() => playTTSResponse("This is a test of the text-to-speech system.")}
                  size="lg"
                  variant="outline"
                  disabled={isRecording}
                >
                  <Volume2 className="w-4 h-4 mr-2" />
                  Test TTS
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Chat History */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <MessageSquare className="w-5 h-5" />
                <span>Conversation History</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96 w-full border rounded-md p-4" ref={scrollAreaRef}>
                <div className="space-y-4">
                  {messages.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      Start a conversation by clicking "Talk" or send a text message
                    </div>
                  ) : (
                    messages.map((message) => (
                      <div key={message.id} className={`flex ${message.speaker === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[85%] rounded-lg px-3 py-2 ${
                            message.speaker === "user"
                              ? "bg-blue-500 text-white"
                              : "bg-slate-100 text-slate-900"
                          }`}
                        >
                          {message.transcript && message.speaker === "user" && (
                            <div className="text-xs opacity-75 mb-1 flex items-center">
                              <Mic className="w-3 h-3 mr-1" />
                              Spoken
                            </div>
                          )}
                          <p className="text-sm">{message.message}</p>
                          <div className="text-xs opacity-50 mt-1">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}