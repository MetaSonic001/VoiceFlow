'use client'

import { useState, useEffect, useRef } from 'react'
import { Phone, PhoneOff, Mic, MicOff, ShieldAlert, Sparkles, Volume2, ShieldCheck, Zap } from 'lucide-react'

// Wireframe Globe Canvas Component
function WireframeGlobe({ isConnected, isSpeaking }: { isConnected: boolean; isSpeaking: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameId = useRef<number>(0)
  const rotation = useRef({ x: 0, y: 0 })
  const wiggleOffset = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set scale based on pixel ratio
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    ctx.scale(dpr, dpr)

    // Sphere data
    const rings = 12
    const sectors = 18
    const radius = 70

    // Animation variables
    let lastTime = 0

    const draw = (time: number) => {
      ctx.clearRect(0, 0, rect.width, rect.height)

      const deltaTime = time - lastTime
      lastTime = time

      // Speed up rotation if connected
      const rotationSpeed = isConnected ? 0.0006 : 0.0002
      rotation.current.y += deltaTime * rotationSpeed
      rotation.current.x = Math.sin(time * 0.0003) * 0.2

      // Speaking wiggle physics
      if (isSpeaking) {
        wiggleOffset.current += 0.12
      } else {
        wiggleOffset.current += 0.01 // very slow idle breath
      }

      const cosX = Math.cos(rotation.current.x)
      const sinX = Math.sin(rotation.current.x)
      const cosY = Math.cos(rotation.current.y)
      const sinY = Math.sin(rotation.current.y)

      const cx = rect.width / 2
      const cy = rect.height / 2

      // Project 3D to 2D
      const getProjectedPoint = (theta: number, phi: number) => {
        // Base sphere coords
        let x3d = Math.sin(theta) * Math.cos(phi)
        let y3d = Math.cos(theta)
        let z3d = Math.sin(theta) * Math.sin(phi)

        // Deform if speaking
        let r = radius
        if (isConnected) {
          if (isSpeaking) {
            // Organic wave deformation based on spherical coordinates
            const wave = Math.sin(theta * 4 + phi * 2 + wiggleOffset.current) * 8
            const noise = Math.cos(theta * 8 - wiggleOffset.current * 1.5) * 4
            r += wave + noise
          } else {
            // Idle breath
            r += Math.sin(wiggleOffset.current + theta) * 1.5
          }
        }

        x3d *= r
        y3d *= r
        z3d *= r

        // Rotate Y
        let x1 = x3d * cosY - z3d * sinY
        let z1 = x3d * sinY + z3d * cosY

        // Rotate X
        let y2 = y3d * cosX - z1 * sinX
        let z2 = y3d * sinX + z1 * cosX

        // Perspective projection
        const distance = 250
        const scale = distance / (distance + z2)
        const x2d = cx + x1 * scale
        const y2d = cy + y2 * scale

        return { x: x2d, y: y2d, depth: z2 }
      };

      // Draw latitude lines (rings)
      for (let r = 1; r < rings - 1; r++) {
        const theta = (r * Math.PI) / (rings - 1)
        ctx.beginPath()

        // Gather points
        const ringPoints = []
        for (let s = 0; s <= sectors; s++) {
          const phi = (s * 2 * Math.PI) / sectors
          ringPoints.push(getProjectedPoint(theta, phi))
        }

        // Draw connected path
        ctx.moveTo(ringPoints[0].x, ringPoints[0].y)
        for (let i = 1; i < ringPoints.length; i++) {
          ctx.lineTo(ringPoints[i].x, ringPoints[i].y)
        }

        // Color based on state: emerald/teal in active call, gray/stone in idle
        const opacity = isConnected ? 0.85 : 0.55
        ctx.strokeStyle = isConnected 
          ? `rgba(52, 211, 153, ${opacity})` // emerald-400 (brighter!)
          : `rgba(168, 162, 158, ${opacity})` // stone-400 (fully visible!)
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Draw longitude lines (sectors)
      for (let s = 0; s < sectors; s++) {
        const phi = (s * 2 * Math.PI) / sectors
        ctx.beginPath()

        const sectorPoints = []
        for (let r = 0; r < rings; r++) {
          const theta = (r * Math.PI) / (rings - 1)
          sectorPoints.push(getProjectedPoint(theta, phi))
        }

        ctx.moveTo(sectorPoints[0].x, sectorPoints[0].y)
        for (let i = 1; i < sectorPoints.length; i++) {
          ctx.lineTo(sectorPoints[i].x, sectorPoints[i].y)
        }

        const opacity = isConnected ? 0.85 : 0.55
        ctx.strokeStyle = isConnected 
          ? `rgba(52, 211, 153, ${opacity})` 
          : `rgba(168, 162, 158, ${opacity})`
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Draw a subtle outer halo glow in active call
      if (isConnected) {
        ctx.beginPath()
        ctx.arc(cx, cy, radius * (isSpeaking ? 1.15 : 1.05), 0, 2 * Math.PI)
        const glowGradient = ctx.createRadialGradient(cx, cy, radius * 0.8, cx, cy, radius * 1.3)
        glowGradient.addColorStop(0, 'rgba(52, 211, 153, 0.15)')
        glowGradient.addColorStop(1, 'rgba(52, 211, 153, 0)')
        ctx.fillStyle = glowGradient
        ctx.fill()
      }

      animationFrameId.current = requestAnimationFrame(draw)
    };

    animationFrameId.current = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(animationFrameId.current)
    }
  }, [isConnected, isSpeaking])

  return <canvas ref={canvasRef} className="w-[180px] h-[180px] aspect-square mx-auto block" />
}

// Agent definitions
interface AgentOption {
  id: string
  name: string
  icon: string
  role: string
  greeting: string
  bgClass: string
}

const AGENTS: AgentOption[] = [
  {
    id: 'infra',
    name: 'VoiceInfra Assistant',
    icon: '🤖',
    role: 'Infrastructure Bot',
    greeting: 'Hello! I am your VoiceFlow Infrastructure Agent. I can help you monitor server latency, trigger deployments, or scale instances. What would you like to check?',
    bgClass: 'from-blue-600/20 to-indigo-600/20 border-blue-500/40 text-blue-400'
  },
  {
    id: 'health',
    name: 'Healthcare Support',
    icon: '🏥',
    role: 'Medical Assistant',
    greeting: 'Hi there, thank you for calling Healthcare Support. I can help you schedule appointments, refill prescriptions, or answer insurance coverage questions. How can I help you today?',
    bgClass: 'from-emerald-600/20 to-teal-600/20 border-emerald-500/40 text-emerald-400'
  },
  {
    id: 'finance',
    name: 'Financial Services',
    icon: '🏦',
    role: 'Wealth Advisor',
    greeting: 'Welcome to VoiceFlow Wealth & Financial Services. I can check your account balances, transfer funds, or connect you with a financial planner. What can I do for you?',
    bgClass: 'from-amber-600/20 to-orange-600/20 border-amber-500/40 text-amber-400'
  },
  {
    id: 'insurance',
    name: 'Insurance Claims',
    icon: '🛡️',
    role: 'Claims Specialist',
    greeting: 'Hello, thank you for calling Insurance Claims. I can help you file a new claim, check the status of an existing claim, or upload documentation. How can I help you today?',
    bgClass: 'from-purple-600/20 to-pink-600/20 border-purple-500/40 text-purple-400'
  }
]

export function InteractiveAgentDemo() {
  const [callState, setCallState] = useState<'idle' | 'connecting' | 'connected'>('idle')
  const [activeAgent, setActiveAgent] = useState<AgentOption>(AGENTS[0])
  const [isMuted, setIsMuted] = useState(false)
  const [isAiSpeaking, setIsAiSpeaking] = useState(false)
  const [timer, setTimer] = useState(0)
  const [captions, setCaptions] = useState('')
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const speakTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Format call timer (e.g. 00:12)
  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  // Handle call button click (Start Call)
  const handleStartCall = () => {
    setCallState('connecting')
    setTimer(0)
    
    // Simulate connection delay
    setTimeout(() => {
      setCallState('connected')
      triggerGreeting(AGENTS[0])
    }, 1500)
  }

  // Trigger agent speaking greeting
  const triggerGreeting = (agent: AgentOption) => {
    if (speakTimeoutRef.current) clearTimeout(speakTimeoutRef.current)
    
    setIsAiSpeaking(true)
    setCaptions(agent.greeting)

    // Simulate AI speaking duration based on length of text
    const duration = agent.greeting.length * 40 // ~40ms per character
    speakTimeoutRef.current = setTimeout(() => {
      setIsAiSpeaking(false)
      setCaptions('[Listening...]')
    }, duration)
  }

  // Handle switching agents during call
  const handleSwitchAgent = (agent: AgentOption) => {
    if (callState !== 'connected') return
    setActiveAgent(agent)
    triggerGreeting(agent)
  }

  // Handle ending the call
  const handleEndCall = () => {
    setCallState('idle')
    setIsMuted(false)
    setIsAiSpeaking(false)
    setCaptions('')
    if (timerRef.current) clearInterval(timerRef.current)
    if (speakTimeoutRef.current) clearTimeout(speakTimeoutRef.current)
  }

  // Timer effect when connected
  useEffect(() => {
    if (callState === 'connected') {
      timerRef.current = setInterval(() => {
        setTimer((prev) => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [callState])

  // Cleanup timeouts
  useEffect(() => {
    return () => {
      if (speakTimeoutRef.current) clearTimeout(speakTimeoutRef.current)
    }
  }, [])

  return (
    <section id="demo" className="py-16 md:py-24 bg-stone-100 border-t border-stone-200">
      <div className="max-w-7xl mx-auto px-8">
        
        {/* Two Columns Grid */}
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          
          {/* Left Column: Text Content and Info */}
          <div className="lg:col-span-5 flex flex-col justify-center text-left">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-orange-100 border border-orange-200 text-orange-800 text-xs font-semibold mb-6 shadow-xs w-fit">
              <span>🎯</span> See Why Competitors Are Stealing Your Customers
            </div>
            <h2 className="font-serif text-4xl lg:text-[2.6rem] xl:text-5xl font-bold text-stone-900 mb-6 leading-tight">
              Talk to Our AI Agent <span className="italic text-emerald-700">Right Now</span>
            </h2>
            <p className="font-serif text-stone-700 text-lg leading-relaxed mb-6">
              Experience instant call answering that never misses revenue. Test the AI that answers every call in under 2 seconds, 24/7.
            </p>
            <div className="bg-emerald-600/10 border border-emerald-600/20 text-emerald-800 font-sans text-xs px-4 py-2.5 rounded-xl mb-8 leading-relaxed">
              Demo requires microphone access — just like your real customers calling in
            </div>

            {/* Stats Bar */}
            <div className="flex flex-col gap-4 font-serif text-base text-stone-600 border-t border-stone-200/60 pt-6">
              <span className="flex items-center gap-1.5">⚡ 2-second response time</span>
              <span className="flex items-center gap-1.5">📞 Real voice conversation</span>
              <span className="flex items-center gap-1.5">🛡️ No installation required</span>
            </div>
          </div>

          {/* Right Column: Interactive Call Box Container */}
          <div className="lg:col-span-7 flex justify-center lg:justify-end w-full">
            <div className="w-full max-w-2xl bg-stone-950 border border-stone-850 rounded-3xl p-6 md:p-8 relative overflow-hidden shadow-2xl min-h-[460px] md:min-h-[500px] flex flex-col justify-between items-center transition-all duration-500">
              
              {/* IDLE STATE */}
              {callState === 'idle' && (
                <div 
                  onClick={handleStartCall}
                  className="flex-1 flex flex-col justify-center items-center w-full cursor-pointer group"
                >
                  <div className="flex-1 flex items-center justify-center min-h-[220px]">
                    <div className="scale-110 md:scale-125 group-hover:scale-130 transition-transform duration-500">
                      <WireframeGlobe isConnected={false} isSpeaking={false} />
                    </div>
                  </div>
                  
                  <div className="text-center mt-6 z-10">
                    <div className="font-serif font-bold text-xl md:text-2xl text-stone-200 group-hover:text-emerald-400 transition-colors flex items-center justify-center gap-2 select-none">
                      👉 Click to Start Live Conversation
                    </div>
                    <p className="font-serif text-stone-400 text-sm mt-3 leading-relaxed max-w-md mx-auto">
                      Test what your competitors&apos; customers experience when they call at 3 AM
                    </p>
                  </div>
                </div>
              )}

              {/* CONNECTING STATE */}
              {callState === 'connecting' && (
                <div className="flex-1 flex flex-col justify-center items-center w-full">
                  <div className="flex-1 flex items-center justify-center">
                    <div className="relative">
                      {/* Pulsing ring backdrop */}
                      <span className="absolute -inset-8 rounded-full bg-emerald-500/10 animate-ping" />
                      <WireframeGlobe isConnected={true} isSpeaking={false} />
                    </div>
                  </div>
                  
                  {/* verification card */}
                  <div className="bg-stone-900 border border-stone-800 rounded-2xl p-5 text-center max-w-sm w-full mx-auto shadow-xl z-10 animate-pulse">
                    <div className="font-serif font-bold text-lg text-stone-100 flex items-center justify-center gap-2 mb-1.5">
                      🚀 Almost there!
                    </div>
                    <p className="font-sans text-stone-400 text-xs">
                      Quick verification to start your live AI conversation
                    </p>
                  </div>
                </div>
              )}

              {/* CONNECTED CALL STATE */}
              {callState === 'connected' && (
                <div className="flex-1 flex flex-col justify-between items-center w-full h-full gap-6">
                  
                  {/* Switch agents block at the top */}
                  <div className="w-full z-10">
                    <div className="text-center text-[10px] uppercase tracking-wider text-stone-500 font-mono mb-3">
                      Switch agents during the call
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {AGENTS.map((agent) => {
                        const isSelected = activeAgent.id === agent.id
                        return (
                          <button
                            key={agent.id}
                            onClick={() => handleSwitchAgent(agent)}
                            className={`p-3 rounded-2xl border transition-all duration-300 flex flex-col items-center justify-center gap-1.5 cursor-pointer relative ${
                              isSelected
                                ? `bg-stone-900 border-emerald-500/80 shadow-[0_0_15px_rgba(16,185,129,0.15)]`
                                : 'bg-stone-900/40 border-stone-800/80 hover:bg-stone-900/80 text-stone-400 hover:text-stone-200'
                            }`}
                          >
                            <span className="text-xl">{agent.icon}</span>
                            <span className="font-serif font-semibold text-[10px] md:text-xs text-stone-200 leading-tight text-center">
                              {agent.name.split(' ')[0]} {agent.name.split(' ')[1] || ''}
                            </span>
                            
                            {/* Glow and pulse indicator dot */}
                            {isSelected && (
                              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 flex items-center justify-center">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-400" />
                                <span className="absolute w-2.5 h-2.5 rounded-full bg-emerald-500/40 animate-ping" />
                              </div>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Sphere and Timer in the Center */}
                  <div className="flex-1 flex flex-col justify-center items-center w-full min-h-[160px]">
                    <div className="relative">
                      <WireframeGlobe isConnected={true} isSpeaking={isAiSpeaking} />
                    </div>
                    
                    {/* Timer pill */}
                    <div className="mt-4 bg-stone-900/80 border border-stone-800/60 rounded-full px-3 py-1 flex items-center gap-2 text-stone-300 text-xs font-mono select-none">
                      <span>⏱️ {formatTimer(timer)}</span>
                      <span className="w-1 h-3 border-l border-stone-700" />
                      <span className="flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-emerald-400 font-semibold uppercase tracking-wider text-[9px]">Connected</span>
                      </span>
                    </div>
                  </div>

                  {/* Live captions / AI Agent Speak Subtitles */}
                  <div className="w-full max-w-xl mx-auto bg-stone-900/50 border border-stone-900/80 rounded-2xl p-4 min-h-[72px] flex items-center justify-center text-center">
                    <p className="font-serif italic text-stone-300 text-sm md:text-base leading-relaxed leading-[1.4]">
                      {isAiSpeaking ? (
                        <span className="text-stone-100 font-bold">{activeAgent.role}: </span>
                      ) : null}
                      {captions}
                    </p>
                  </div>

                  {/* Bottom controls panel */}
                  <div className="w-full bg-stone-900 border border-stone-850 rounded-2xl px-6 py-3 flex items-center justify-between mt-auto">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setIsMuted(!isMuted)}
                        className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors cursor-pointer border ${
                          isMuted 
                            ? 'bg-red-950/40 border-red-900/50 text-red-400 hover:bg-red-950/60' 
                            : 'bg-stone-800 border-stone-700 text-stone-300 hover:bg-stone-750 hover:text-white'
                        }`}
                      >
                        {isMuted ? <MicOff size={16} /> : <Mic size={16} />}
                      </button>
                      <span className="text-xs font-mono text-stone-400 select-none">
                        {isMuted ? 'Muted' : 'Mic active'}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleEndCall}
                        className="w-10 h-10 rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center transition-colors cursor-pointer shadow-lg shadow-red-950/30"
                      >
                        <PhoneOff size={16} />
                      </button>
                      <span className="text-xs font-mono text-stone-400 select-none">
                        End Call
                      </span>
                    </div>
                  </div>

                </div>
              )}
            </div>
          </div>
        </div>

        {/* Lower Features Block (What You'll Experience) */}
        <div className="mt-24 border-t border-stone-200 pt-16">
          <h3 className="font-serif text-2xl lg:text-3xl font-bold text-stone-900 text-center mb-12">
            What You&apos;ll Experience in This Demo
          </h3>

          <div className="grid md:grid-cols-3 gap-8 text-center max-w-5xl mx-auto mb-16">
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-stone-900 flex items-center justify-center text-stone-100 mx-auto">
                <Zap size={22} />
              </div>
              <h4 className="font-serif font-bold text-lg text-stone-900">Instant Response</h4>
              <p className="font-serif text-stone-600 text-sm leading-relaxed max-w-xs mx-auto">
                No hold music. No &quot;please wait.&quot; Just immediate, intelligent conversation.
              </p>
            </div>

            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-stone-900 flex items-center justify-center text-stone-100 mx-auto">
                <Sparkles size={22} />
              </div>
              <h4 className="font-serif font-bold text-lg text-stone-900">Human-Like Conversation</h4>
              <p className="font-serif text-stone-600 text-sm leading-relaxed max-w-xs mx-auto">
                Natural speech patterns, interruption handling, and contextual responses.
              </p>
            </div>

            <div className="space-y-4">
              <div className="w-12 h-12 rounded-xl bg-stone-900 flex items-center justify-center text-stone-100 mx-auto">
                <Volume2 size={22} />
              </div>
              <h4 className="font-serif font-bold text-lg text-stone-900">Real Actions</h4>
              <p className="font-serif text-stone-600 text-sm leading-relaxed max-w-xs mx-auto">
                Watch it schedule appointments, answer questions, and capture lead information.
              </p>
            </div>
          </div>

          {/* Footer Highlights */}
          <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 font-serif text-sm text-stone-600 border-t border-stone-200/50 pt-8 max-w-xl mx-auto">
            <span className="flex items-center gap-1.5">⏱️ Demo takes 2-3 minutes</span>
            <span className="flex items-center gap-1.5">🔒 No personal info required</span>
            <span className="flex items-center gap-1.5">📞 Real AI, not pre-recorded</span>
          </div>
        </div>

      </div>
    </section>
  )
}
