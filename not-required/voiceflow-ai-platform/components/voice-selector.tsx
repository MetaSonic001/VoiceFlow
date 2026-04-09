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
  Info,
  Clock,
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
  const [cloneErrorTips, setCloneErrorTips] = useState<string[]>([])
  const [clonedVoiceId, setClonedVoiceId] = useState<string | null>(
    value?.startsWith("clone-") ? value : null
  )
  const [cloneTestUrl, setCloneTestUrl] = useState<string | null>(null)

  // Recording state
  const [recording, setRecording] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Audio level visualization
  const [audioLevel, setAudioLevel] = useState(0)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animFrameRef = useRef<number | null>(null)

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
      if (timerRef.current) clearInterval(timerRef.current)
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
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
      setCloneErrorTips([])
      setClonedVoiceId(null)
      setCloneTestUrl(null)
    }
  }

  const uploadAndClone = async () => {
    if (!cloneFile) return
    setCloning(true)
    setCloneError("")
    setCloneErrorTips([])
    try {
      const result = await apiClient.cloneVoice(cloneFile)
      setClonedVoiceId(result.voiceId)
      setCloneTestUrl(result.testAudioUrl)
      onChange(result.voiceId)
    } catch (err: any) {
      const msg =
        err?.response?.error || err?.message || "Voice cloning failed"
      setCloneError(msg)
      // Extract tips from backend response if available
      const tips = err?.response?.tips || err?.tips || []
      setCloneErrorTips(Array.isArray(tips) ? tips : [])
    } finally {
      setCloning(false)
    }
  }

  // ── Clone: in-browser recording with level monitoring ──────────────────

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      })
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" })
      chunksRef.current = []

      // Audio level monitoring
      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      const updateLevel = () => {
        if (!analyserRef.current) return
        const data = new Uint8Array(analyserRef.current.frequencyBinCount)
        analyserRef.current.getByteFrequencyData(data)
        const avg = data.reduce((sum, v) => sum + v, 0) / data.length
        setAudioLevel(Math.min(100, (avg / 128) * 100))
        animFrameRef.current = requestAnimationFrame(updateLevel)
      }
      updateLevel()

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        audioCtx.close()
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
        setAudioLevel(0)
        analyserRef.current = null
        const blob = new Blob(chunksRef.current, { type: "audio/webm" })
        const file = new File([blob], "recording.webm", { type: "audio/webm" })
        setCloneFile(file)
        setCloneError("")
        setCloneErrorTips([])
        setClonedVoiceId(null)
        setCloneTestUrl(null)
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
      setRecordingSeconds(0)

      // Timer
      timerRef.current = setInterval(() => {
        setRecordingSeconds((s) => s + 1)
      }, 1000)
    } catch (err) {
      setCloneError("Microphone access denied. Please allow microphone access in your browser settings.")
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`

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
              Record or upload 10–60 seconds of clear speech. Your agent will sound like this voice.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Quality guidance panel */}
            <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3 space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-blue-800 dark:text-blue-200">
                <Info className="w-4 h-4" />
                What makes a good reference clip
              </div>
              <ul className="text-xs text-blue-700 dark:text-blue-300 space-y-1 ml-6 list-disc">
                <li><strong>Quiet room</strong> — no background music, TV, traffic, or other people talking</li>
                <li><strong>One speaker</strong> — only the voice you want to clone, speaking naturally</li>
                <li><strong>10–30 seconds ideal</strong> — read a paragraph aloud at normal pace</li>
                <li><strong>No WhatsApp/phone recordings</strong> — compressed phone audio produces poor clones</li>
                <li><strong>Hold device 15–20 cm away</strong> — avoid breathing/plosive sounds on the mic</li>
              </ul>
              <p className="text-xs text-blue-600 dark:text-blue-400 italic">
                Tip: Try reading this aloud — "The quick brown fox jumps over the lazy dog. She sells seashells by the seashore. How much wood would a woodchuck chuck if a woodchuck could chuck wood?"
              </p>
            </div>

            {/* In-browser recording */}
            <div className="space-y-2">
              <Label>Option 1: Record directly</Label>
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  variant={recording ? "destructive" : "outline"}
                  onClick={recording ? stopRecording : startRecording}
                  className="min-w-[140px]"
                >
                  {recording ? (
                    <>
                      <Square className="w-4 h-4 mr-2" />
                      Stop Recording
                    </>
                  ) : (
                    <>
                      <Mic className="w-4 h-4 mr-2" />
                      Start Recording
                    </>
                  )}
                </Button>
                {recording && (
                  <div className="flex items-center gap-3 flex-1">
                    <div className="flex items-center gap-1.5 text-sm text-red-600 font-mono">
                      <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      <Clock className="w-3.5 h-3.5" />
                      {formatTime(recordingSeconds)}
                    </div>
                    {/* Level meter */}
                    <div className="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-75"
                        style={{
                          width: `${audioLevel}%`,
                          backgroundColor: audioLevel > 80 ? '#ef4444' : audioLevel > 40 ? '#22c55e' : '#94a3b8',
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
              {recording && (
                <p className="text-xs text-muted-foreground">
                  {recordingSeconds < 5 && "Keep going — aim for at least 10 seconds…"}
                  {recordingSeconds >= 5 && recordingSeconds < 10 && "Good start — a few more seconds for better quality…"}
                  {recordingSeconds >= 10 && recordingSeconds < 30 && "Great length! You can stop anytime, or keep going for the best results."}
                  {recordingSeconds >= 30 && recordingSeconds < 60 && "Excellent! This is more than enough. Press Stop whenever you're ready."}
                  {recordingSeconds >= 60 && "Maximum duration reached — press Stop to finish."}
                </p>
              )}
              {!recording && recordingSeconds > 0 && cloneFile?.name === "recording.webm" && (
                <p className="text-xs text-green-600">
                  <CheckCircle className="w-3 h-3 inline mr-1" />
                  Recorded {formatTime(recordingSeconds)} of audio — ready to clone
                </p>
              )}
            </div>

            {/* Or file upload */}
            <div className="space-y-2">
              <Label>Option 2: Upload a file</Label>
              <Input
                type="file"
                accept="audio/wav,audio/mpeg,audio/mp3,audio/webm,audio/flac,audio/ogg,audio/m4a"
                onChange={handleFileChange}
              />
              {cloneFile && cloneFile.name !== "recording.webm" && (
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
              className="w-full"
            >
              {cloning ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Cloning voice… (this takes 5–15 seconds)
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  {cloneFile ? "Upload & Clone Voice" : "Record or upload audio first"}
                </>
              )}
            </Button>

            {/* Error with tips */}
            {cloneError && (
              <div className="space-y-2">
                <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="text-sm font-medium">{cloneError}</span>
                    {cloneErrorTips.length > 0 && (
                      <ul className="text-xs space-y-0.5 list-disc ml-4 text-red-700 dark:text-red-300">
                        {cloneErrorTips.map((tip, i) => (
                          <li key={i}>{tip}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Success + play test */}
            {clonedVoiceId && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-200">
                  <CheckCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="text-sm font-medium">
                    Voice cloned successfully! Listen to the preview below.
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
