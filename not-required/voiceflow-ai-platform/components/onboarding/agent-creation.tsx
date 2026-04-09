"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import MotionWrapper from "@/components/ui/MotionWrapper"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Bot,
  Phone,
  MessageSquare,
  Mail,
  Headphones,
  CalendarCheck,
  UserCheck,
  BriefcaseBusiness,
  Megaphone,
  ArrowRight,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api-client"
import type { LucideIcon } from "lucide-react"

// ── Icon mapping (keyed by icon string from DB) ─────────────────────────────
const ICON_MAP: Record<string, LucideIcon> = {
  headphones: Headphones,
  megaphone: Megaphone,
  "calendar-check": CalendarCheck,
  "user-check": UserCheck,
  "briefcase-business": BriefcaseBusiness,
  phone: Phone,
}

// ── Fallback persona descriptions (used for the editable persona field) ─────
const PERSONA_MAP: Record<string, string> = {
  "customer-support":
    "You are a friendly and efficient customer support agent. You listen carefully, empathise with the customer, and resolve issues quickly using the company knowledge base. If you don't know the answer, you offer to escalate to a human agent.",
  "cold-calling":
    "You are a confident outbound sales caller. You introduce the product concisely, handle objections politely, and always aim to book a follow-up meeting or demo. You respect the prospect's time and never pressure.",
  "appointment-booking":
    "You are an efficient appointment-booking assistant. You check available slots, confirm details with the caller, send confirmation, and handle rescheduling or cancellations gracefully.",
  "lead-qualification":
    "You are a lead-qualification specialist. You ask structured discovery questions about the prospect's needs, budget, timeline, and decision process. You score the lead and route qualified ones to the sales team.",
  "hr-helpdesk":
    "You are an internal HR helpdesk agent. You answer employee questions about company policies, benefits, leave, and onboarding. You reference the HR knowledge base and escalate sensitive topics to a human HR representative.",
  "sales-followup":
    "You are a sales follow-up agent. You check in on open proposals, answer outstanding questions, handle pricing negotiations courteously, and guide the prospect toward closing the deal.",
}

// ── Hardcoded fallback (used if the API is unreachable) ─────────────────────
const FALLBACK_TEMPLATES = [
  { id: "customer-support", name: "Customer Support", description: "Handles inbound support queries, troubleshooting, and FAQ", icon: "headphones" },
  { id: "cold-calling", name: "Cold Calling", description: "Outbound sales calls with pitch and objection handling", icon: "megaphone" },
  { id: "appointment-booking", name: "Appointment Booking", description: "Schedules, confirms, and manages appointments or demos", icon: "calendar-check" },
  { id: "lead-qualification", name: "Lead Qualification", description: "Qualifies inbound leads with structured discovery questions", icon: "user-check" },
  { id: "hr-helpdesk", name: "HR Helpdesk", description: "Answers employee questions about policies, benefits, and leave", icon: "briefcase-business" },
  { id: "sales-followup", name: "Sales Follow-up", description: "Follows up on proposals, quotes, and guides prospects to close", icon: "phone" },
]

interface TemplateItem {
  id: string
  name: string
  description: string
  icon: string | null
}

// ── Channels ────────────────────────────────────────────────────────────────
const CHANNELS = [
  { id: "phone", label: "Phone Calls", icon: Phone, description: "Handle inbound and outbound voice calls" },
  { id: "chat", label: "Website Chat", icon: MessageSquare, description: "Embed chat widget on your website" },
  { id: "whatsapp", label: "WhatsApp", icon: MessageSquare, description: "Connect via WhatsApp Business API" },
  { id: "email", label: "Email", icon: Mail, description: "Respond to email inquiries" },
]

// ── Component ───────────────────────────────────────────────────────────────
interface AgentCreationProps {
  onComplete: (data: any) => void
  data?: Record<string, any>
  initialData?: Record<string, any>
}

export function AgentCreation({ onComplete, data, initialData }: AgentCreationProps) {
  const [templates, setTemplates] = useState<TemplateItem[]>(FALLBACK_TEMPLATES)
  const [loadingTemplates, setLoadingTemplates] = useState(true)
  const [selectedTemplate, setSelectedTemplate] = useState<string>("")
  const [agentName, setAgentName] = useState("")
  const [persona, setPersona] = useState("")
  const [channels, setChannels] = useState<string[]>([])
  const { toast } = useToast()

  // Load templates from API
  useEffect(() => {
    ;(async () => {
      try {
        const res = await apiClient.getAgentTemplates()
        if (res.templates?.length > 0) {
          setTemplates(res.templates)
        }
      } catch {
        // Use fallback
      } finally {
        setLoadingTemplates(false)
      }
    })()
  }, [])

  // Hydrate from parent / saved progress
  useEffect(() => {
    const saved = data?.agent || initialData?.agent
    if (saved) {
      if (saved.templateId) setSelectedTemplate(saved.templateId)
      if (saved.agentName) setAgentName(saved.agentName)
      if (saved.description) setPersona(saved.description)
      if (saved.channels) setChannels(saved.channels)
    }
  }, [data, initialData])

  // Auto-fill persona when template changes
  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplate(templateId)
    if (PERSONA_MAP[templateId]) {
      setPersona(PERSONA_MAP[templateId])
    }
  }

  const handleChannelToggle = (channelId: string, checked: boolean) => {
    setChannels((prev) => (checked ? [...prev, channelId] : prev.filter((c) => c !== channelId)))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const tpl = templates.find((t) => t.id === selectedTemplate)
    toast({ title: "Agent saved", description: "Agent details saved locally" })
    onComplete({
      agent: {
        agentName,
        templateId: selectedTemplate,
        role: tpl?.name || selectedTemplate,
        description: persona,
        channels,
      },
    })
  }

  const canSubmit = !!selectedTemplate && !!agentName.trim() && channels.length > 0

  return (
    <MotionWrapper>
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto">
            <Bot className="w-6 h-6 text-accent" />
          </div>
          <h2 className="text-2xl font-bold">What will your agent do?</h2>
          <p className="text-muted-foreground text-sm max-w-md mx-auto">
            Pick a template to start with — your agent gets a purpose and personality right away.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8 max-w-2xl mx-auto">
          {/* ── Template cards ── */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {loadingTemplates ? (
              <div className="col-span-full flex justify-center py-6">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : templates.map((tpl) => {
              const Icon = (tpl.icon && ICON_MAP[tpl.icon]) || Bot
              const selected = selectedTemplate === tpl.id
              return (
                <button
                  key={tpl.id}
                  type="button"
                  onClick={() => handleTemplateSelect(tpl.id)}
                  className={cn(
                    "relative text-left p-4 rounded-xl border-2 transition-all",
                    selected
                      ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                      : "border-border hover:border-primary/40 hover:bg-muted/40"
                  )}
                >
                  <Icon
                    className={cn(
                      "w-5 h-5 mb-2",
                      selected ? "text-primary" : "text-muted-foreground"
                    )}
                  />
                  <p className="font-semibold text-sm">{tpl.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-snug">
                    {tpl.description}
                  </p>
                  {selected && (
                    <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                      <svg className="w-3 h-3 text-primary-foreground" viewBox="0 0 12 12" fill="none">
                        <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  )}
                </button>
              )
            })}
          </div>

          {/* ── Agent name ── */}
          <div className="space-y-2">
            <Label htmlFor="agentName">Agent Name *</Label>
            <Input
              id="agentName"
              placeholder='e.g., "Priya", "Support Bot", "Alex"'
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              className="rounded-xl h-11"
              required
            />
          </div>

          {/* ── Persona (auto-filled, editable) ── */}
          <div className="space-y-2">
            <Label htmlFor="persona">
              Agent Persona{" "}
              <span className="text-xs text-muted-foreground font-normal">— auto-filled from template, editable</span>
            </Label>
            <Textarea
              id="persona"
              placeholder="Select a template above to auto-fill, or write your own persona…"
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              rows={4}
              className="rounded-xl"
            />
          </div>

          {/* ── Communication channels ── */}
          <div className="space-y-3">
            <Label>Communication Channels *</Label>
            <p className="text-sm text-muted-foreground">Select how customers will interact with your agent</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {CHANNELS.map((ch) => {
                const Icon = ch.icon
                return (
                  <div
                    key={ch.id}
                    className="flex items-start space-x-3 p-4 border border-border rounded-xl"
                  >
                    <Checkbox
                      id={ch.id}
                      checked={channels.includes(ch.id)}
                      onCheckedChange={(checked) => handleChannelToggle(ch.id, checked as boolean)}
                    />
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-0.5">
                        <Icon className="w-4 h-4 text-accent" />
                        <Label htmlFor={ch.id} className="font-medium">
                          {ch.label}
                        </Label>
                      </div>
                      <p className="text-xs text-muted-foreground">{ch.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* ── Submit ── */}
          <Button
            type="submit"
            className="w-full rounded-xl h-12 text-base gap-2"
            disabled={!canSubmit}
          >
            Continue to Knowledge Upload
            <ArrowRight className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </MotionWrapper>
  )
}
