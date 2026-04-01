"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Play,
  Square,
  Upload,
  Mic,
  Loader2,
  CheckCircle,
  AlertCircle,
  Volume2,
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface PresetVoice {
  id: string
  name: string
  description: string
  sampleUrl: string | null
}

interface VoiceSelectorProps {
  value: string | null
  onChange: (voiceId: string, voiceCloneSourceUrl?: string) => void
}

export function VoiceSelector({ value, onChange }: VoiceSelectorProps) {
  const [mode, setMode] = useState<"preset" | "clone">(
    value?.startsWith("clone-") ? "clone" : "preset"
  )
  const [presets, setPresets] = useState<PresetVoice[]>([])
  const [presetsLoading, setPresetsLoading] = useState(true)
  const [playingId, setPlayingId] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Clone state
  const [cloneFile, setCloneFile] = useState<File | null>(null)
  const [cloning, setCloning] = useState(false)
  const [cloneError, setCloneError] = useState("")
  const [clonedVoiceId, setClonedVoiceId] = useState<string | null>(
    value?.startsWith("clone-") ? value : null
  )
  const [cloneTestUrl, setCloneTestUrl] = useState<string | null>(null)

  // Recording state
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  // Load preset voices
  useEffect(() => {
    const loadPresets = async () => {
      try {
        const data = await apiClient.getPresetVoices()
        setPresets(data.voices || [])
      } catch (err) {
        console.error("Failed to load preset voices:", err)
      } finally {
        setPresetsLoading(false)
      }
    }
    loadPresets()
  }, [])

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  const playAudio = useCallback((url: string, id: string) => {
    if (audioRef.current) {
      audioRef.current.pause()
    }
    if (playingId === id) {
      setPlayingId(null)
      return
    }
    const audio = new Audio(url)
    audioRef.current = audio
    setPlayingId(id)
    audio.onended = () => setPlayingId(null)
    audio.onerror = () => setPlayingId(null)
    audio.play().catch(() => setPlayingId(null))
  }, [playingId])

  const selectPreset = (presetId: string) => {
    onChange(presetId)
    setMode("preset")
  }

  // ── Clone: file upload ─────────────────────────────────────────────────

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setCloneFile(file)
      setCloneError("")
      setClonedVoiceId(null)
      setCloneTestUrl(null)
    }
  }

  const uploadAndClone = async () => {
    if (!cloneFile) return
    setCloning(true)
    setCloneError("")
    try {
      const result = await apiClient.cloneVoice(cloneFile)
      setClonedVoiceId(result.voiceId)
      setCloneTestUrl(result.testAudioUrl)
      onChange(result.voiceId)
    } catch (err: any) {
      const msg =
        err?.response?.error || err?.message || "Voice cloning failed"
      setCloneError(msg)
    } finally {
      setCloning(false)
    }
  }

  // ── Clone: in-browser recording ─────────────────────────────────────────

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" })
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        const file = new File([blob], "recording.webm", { type: "audio/webm" })
        setCloneFile(file)
        setCloneError("")
        setClonedVoiceId(null)
        setCloneTestUrl(null)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch (err) {
      setCloneError("Microphone access denied. Please allow microphone access.")
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="flex gap-2">
        <Button
          type="button"
          variant={mode === "preset" ? "default" : "outline"}
          onClick={() => setMode("preset")}
          size="sm"
        >
          <Volume2 className="w-4 h-4 mr-2" />
          Preset Voices
        </Button>
        <Button
          type="button"
          variant={mode === "clone" ? "default" : "outline"}
          onClick={() => setMode("clone")}
          size="sm"
        >
          <Mic className="w-4 h-4 mr-2" />
          Clone a Voice
        </Button>
      </div>

      {/* ── Preset mode ─────────────────────────────────────────────────── */}
      {mode === "preset" && (
        <div className="space-y-3">
          {presetsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              Loading voices…
            </div>
          ) : presets.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4">
              No preset voices available. Make sure the TTS service is running.
            </p>
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {presets.map((preset) => (
                <div
                  key={preset.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    value === preset.id
                      ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                      : "border-border hover:border-primary/50"
                  }`}
                  onClick={() => selectPreset(preset.id)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medium">{preset.name}</h4>
                    <div className="flex items-center gap-1">
                      {value === preset.id && (
                        <Badge variant="default" className="text-xs">
                          Selected
                        </Badge>
                      )}
                      {preset.sampleUrl && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0"
                          onClick={(e) => {
                            e.stopPropagation()
                            playAudio(preset.sampleUrl!, preset.id)
                          }}
                        >
                          {playingId === preset.id ? (
                            <Square className="w-3 h-3" />
                          ) : (
                            <Play className="w-3 h-3" />
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {preset.description}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Clone mode ──────────────────────────────────────────────────── */}
      {mode === "clone" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Clone a Custom Voice</CardTitle>
            <CardDescription>
              Upload 5–60 seconds of clean audio. Single speaker, no background
              noise, natural speech. This becomes your agent's voice.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* File upload */}
            <div className="space-y-2">
              <Label>Audio File</Label>
              <div className="flex gap-2">
                <Input
                  type="file"
                  accept="audio/wav,audio/mpeg,audio/mp3,audio/webm"
                  onChange={handleFileChange}
                  className="flex-1"
                />
                {/* Record button */}
                <Button
                  type="button"
                  variant="outline"
                  onClick={recording ? stopRecording : startRecording}
                  className={recording ? "text-red-600 border-red-300" : ""}
                >
                  {recording ? (
                    <>
                      <Square className="w-4 h-4 mr-1" />
                      Stop
                    </>
                  ) : (
                    <>
                      <Mic className="w-4 h-4 mr-1" />
                      Record
                    </>
                  )}
                </Button>
              </div>
              {cloneFile && (
                <p className="text-xs text-muted-foreground">
                  Selected: {cloneFile.name} (
                  {(cloneFile.size / 1024).toFixed(0)} KB)
                </p>
              )}
            </div>

            {/* Clone button */}
            <Button
              type="button"
              onClick={uploadAndClone}
              disabled={!cloneFile || cloning}
            >
              {cloning ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Cloning voice… (this takes 5–15 seconds)
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload & Clone Voice
                </>
              )}
            </Button>

            {/* Error */}
            {cloneError && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span className="text-sm">{cloneError}</span>
              </div>
            )}

            {/* Success + play test */}
            {clonedVoiceId && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200 text-green-800">
                  <CheckCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm font-medium">
                    Voice cloned successfully!
                  </span>
                </div>
                {cloneTestUrl && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      playAudio(cloneTestUrl, "clone-test")
                    }
                  >
                    {playingId === "clone-test" ? (
                      <Square className="w-4 h-4 mr-2" />
                    ) : (
                      <Play className="w-4 h-4 mr-2" />
                    )}
                    Play Test Sample
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
