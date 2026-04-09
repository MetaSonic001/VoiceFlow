"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Search,
  Loader2,
  CheckCircle2,
  Globe,
  Sparkles,
  RefreshCw,
  ArrowRight,
  Lock,
} from "lucide-react"
import { apiClient } from "@/lib/api-client"
import MotionWrapper from "@/components/ui/MotionWrapper"

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────
interface CompanySuggestion {
  id: string
  name: string
  domain: string
  industry: string
  description?: string
}

interface CompanySetupProps {
  onComplete: (data: any) => void
}

// ────────────────────────────────────────────────────────────────────────────
// Clearbit logo with first-letter fallback
// ────────────────────────────────────────────────────────────────────────────
function CompanyLogo({
  domain,
  name,
  size = 40,
}: {
  domain: string
  name: string
  size?: number
}) {
  const [failed, setFailed] = useState(false)

  if (!domain || failed) {
    return (
      <div
        style={{ width: size, height: size }}
        className="rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0"
      >
        <span
          className="font-bold text-primary"
          style={{ fontSize: size * 0.4 }}
        >
          {name[0]?.toUpperCase()}
        </span>
      </div>
    )
  }

  return (
    <img
      src={`https://logo.clearbit.com/${domain}`}
      alt={`${name} logo`}
      width={size}
      height={size}
      style={{ width: size, height: size }}
      className="rounded-xl object-contain flex-shrink-0 bg-white border border-border/40"
      onError={() => setFailed(true)}
    />
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Component
// ────────────────────────────────────────────────────────────────────────────
export function CompanySetup({ onComplete }: CompanySetupProps) {
  // search
  const [query, setQuery]               = useState("")
  const [suggestions, setSuggestions]   = useState<CompanySuggestion[]>([])
  const [isSearching, setIsSearching]   = useState(false)
  const [dropOpen, setDropOpen]         = useState(false)

  // selection
  const [locked, setLocked]             = useState<CompanySuggestion | null>(null)
  const [isManual, setIsManual]         = useState(false)
  const [manualName, setManualName]     = useState("")

  // second-stage form (shown after locking a company)
  const [websiteUrl, setWebsiteUrl]     = useState("")
  const [industry, setIndustry]         = useState("")
  const [useCase, setUseCase]           = useState("")

  // submit / scraping state
  const [isSaving, setIsSaving]         = useState(false)

  const { toast }      = useToast()
  const inputRef       = useRef<HTMLInputElement>(null)
  const dropRef        = useRef<HTMLDivElement>(null)
  const debounceTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ── Restore saved progress ──────────────────────────────────────────────
  useEffect(() => {
    ;(async () => {
      try {
        const prog = await apiClient.getOnboardingProgress()
        if (prog?.exists && prog.data?.company) {
          const c = prog.data.company
          if (c.companyName) {
            // Reconstruct locked state
            const fake: CompanySuggestion = {
              id:       c.id || "restored",
              name:     c.companyName,
              domain:   c.domain || "",
              industry: c.industry || "",
            }
            setLocked(fake)
            setQuery(c.companyName)
            setWebsiteUrl(c.websiteUrl || "")
            setIndustry(c.industry || "")
            setUseCase(c.useCase || "")
          }
        }
      } catch { /* ignore */ }
    })()
  }, [])

  // ── Close dropdown on outside click ───────────────────────────────────
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropRef.current   && !dropRef.current.contains(e.target as Node) &&
        inputRef.current  && !inputRef.current.contains(e.target as Node)
      ) {
        setDropOpen(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  // ── Debounced search ───────────────────────────────────────────────────
  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setQuery(val)

    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    if (!val.trim()) { setSuggestions([]); setDropOpen(false); return }

    debounceTimer.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const res = await apiClient.searchCompanies(val.trim())
        setSuggestions(res.companies || [])
        setDropOpen(true)
      } catch {
        setSuggestions([])
      } finally {
        setIsSearching(false)
      }
    }, 280)
  }

  // ── Lock a company from the list ───────────────────────────────────────
  const handleSelect = (company: CompanySuggestion) => {
    setLocked(company)
    setQuery(company.name)
    setDropOpen(false)
    setIsManual(false)
    setIndustry(company.industry.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-"))
    setWebsiteUrl(company.domain ? `https://${company.domain}` : "")
  }

  // ── Enter manually ─────────────────────────────────────────────────────
  const handleManual = () => {
    setIsManual(true)
    setDropOpen(false)
    setManualName(query)
    setLocked({
      id:       "manual",
      name:     query || "My Company",
      domain:   "",
      industry: "",
    })
  }

  // ── Submit → parent's onComplete handles API call + scraping ──────────
  const handleContinue = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!locked) return
    setIsSaving(true)

    const companyName = isManual ? manualName.trim() || locked.name : locked.name

    try {
      // Persist progress so we can restore if user comes back
      await apiClient.saveOnboardingProgress({
        current_step: 1,
        data: {
          company: {
            id:          locked.id,
            companyName,
            domain:      locked.domain,
            industry,
            useCase,
            websiteUrl,
          },
        },
      })
    } catch { /* non-fatal */ }

    // Hand off to onboarding-flow which will call saveCompanyProfile
    // (triggering the actual scrape) then advance the wizard
    onComplete({
      company: {
        id:          locked.id,
        companyName,
        domain:      locked.domain,
        industry,
        useCase,
        websiteUrl,
      },
    })
    setIsSaving(false)
  }

  const canContinue = !!locked && !!useCase && !!industry

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-8">

      {/* ── Header ── */}
      <div className="text-center space-y-2">
        <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
          <Search className="w-6 h-6 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">Which company are you setting up VoiceFlow for?</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          Search for your company or enter it manually. We'll automatically gather your public information and load it into your agent's knowledge base.
        </p>
      </div>

      <form onSubmit={handleContinue} className="space-y-6 max-w-lg mx-auto">

        {/* ── Phase 1 — Search (shown until a company is locked) ── */}
        {!locked && (
          <div className="relative">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground pointer-events-none" />
              {isSearching
                ? <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground animate-spin" />
                : null
              }
              <Input
                ref={inputRef}
                value={query}
                onChange={handleQueryChange}
                onFocus={() => suggestions.length > 0 && setDropOpen(true)}
                placeholder="Type your company name…"
                className="h-14 pl-11 pr-11 text-base rounded-xl border-2 focus-visible:ring-0 focus:border-primary transition-colors"
                autoFocus
              />
            </div>

            {/* Dropdown */}
            {dropOpen && (
              <div
                ref={dropRef}
                className="absolute z-50 left-0 right-0 mt-2 bg-background border border-border rounded-xl shadow-xl overflow-hidden"
              >
                {suggestions.length === 0 && !isSearching ? (
                  <p className="px-4 py-3 text-sm text-muted-foreground text-center">
                    No results — try a different name
                  </p>
                ) : (
                  suggestions.map((company) => (
                    <button
                      key={company.id}
                      type="button"
                      onClick={() => handleSelect(company)}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-accent/70 transition-colors text-left"
                    >
                      <CompanyLogo domain={company.domain} name={company.name} size={40} />
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm">{company.name}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {company.industry}
                          {company.description ? ` · ${company.description}` : ""}
                        </p>
                      </div>
                      <span className="text-xs text-muted-foreground flex-shrink-0">
                        {company.domain}
                      </span>
                    </button>
                  ))
                )}

                {/* Manual option — always visible at bottom */}
                <button
                  type="button"
                  onClick={handleManual}
                  className="w-full flex items-center gap-3 px-4 py-3 border-t border-border/60 hover:bg-accent/50 transition-colors text-left"
                >
                  <div className="w-10 h-10 rounded-xl bg-muted border border-border flex items-center justify-center flex-shrink-0">
                    <span className="text-muted-foreground font-bold text-lg leading-none">+</span>
                  </div>
                  <div>
                    <p className="font-semibold text-sm">My company isn't listed</p>
                    <p className="text-xs text-muted-foreground">Enter details manually</p>
                  </div>
                </button>
              </div>
            )}

            {/* Hint before first keystroke */}
            {!query && (
              <p className="text-center text-xs text-muted-foreground mt-3">
                Start typing to search any company, or click "My company isn't listed" to enter manually
              </p>
            )}
          </div>
        )}

        {/* ── Phase 2 — Company locked ── */}
        {locked && (
          <>
            {/* Locked company card */}
            <div className="flex items-center gap-4 p-4 rounded-2xl border-2 border-primary/40 bg-primary/5">
              <CompanyLogo domain={locked.domain} name={locked.name} size={48} />
              <div className="flex-1 min-w-0">
                {isManual ? (
                  <Input
                    value={manualName}
                    onChange={(e) => {
                      setManualName(e.target.value)
                      setLocked({ ...locked, name: e.target.value })
                    }}
                    placeholder="Company name"
                    className="h-8 text-base font-semibold border-0 border-b rounded-none px-0 focus-visible:ring-0"
                  />
                ) : (
                  <p className="font-bold text-base">{locked.name}</p>
                )}
                <p className="text-xs text-muted-foreground mt-0.5">
                  {locked.domain || "No domain set"}
                </p>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-primary font-medium">
                <Lock className="w-3.5 h-3.5" />
                <span>Locked</span>
              </div>
            </div>

            {/* Website URL */}
            <div className="space-y-2">
              <Label htmlFor="websiteUrl" className="flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-muted-foreground" />
                Company website
              </Label>
              <Input
                id="websiteUrl"
                placeholder="https://yourcompany.com"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                className="rounded-xl"
              />
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 flex-shrink-0" />
                We'll scrape this site and add the content to your agent's knowledge base when you continue.
              </p>
            </div>

            {/* Industry */}
            <div className="space-y-2">
              <Label>Industry *</Label>
              <Select value={industry} onValueChange={setIndustry}>
                <SelectTrigger className="rounded-xl h-11">
                  <SelectValue placeholder="Select industry" />
                </SelectTrigger>
                <SelectContent>
                  {[
                    ["technology","Technology"],["finance","Finance"],
                    ["healthcare","Healthcare"],["retail","Retail"],
                    ["education","Education"],["real-estate","Real Estate"],
                    ["consulting","Consulting"],["food-beverage","Food & Beverage"],
                    ["automotive","Automotive"],["telecom","Telecom"],
                    ["logistics","Logistics"],["fmcg","FMCG"],
                    ["hospitality","Hospitality"],["gaming","Gaming"],
                    ["travel","Travel"],["manufacturing","Manufacturing"],
                    ["services","Services"],["other","Other"],
                  ].map(([val, label]) => (
                    <SelectItem key={val} value={val}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Primary use case */}
            <div className="space-y-2">
              <Label>What will your AI agent primarily handle? *</Label>
              <Select value={useCase} onValueChange={setUseCase}>
                <SelectTrigger className="rounded-xl h-11">
                  <SelectValue placeholder="Select the main purpose" />
                </SelectTrigger>
                <SelectContent>
                  {[
                    ["customer-support", "Customer Support"],
                    ["sales-lead-qualification", "Sales & Lead Qualification"],
                    ["appointment-scheduling", "Appointment Scheduling"],
                    ["cold-calling", "Cold Calling / Outbound"],
                    ["hr-internal-helpdesk", "HR & Internal Helpdesk"],
                    ["order-status-tracking", "Order Status & Tracking"],
                    ["general-inquiries", "General Business Inquiries"],
                  ].map(([val, label]) => (
                    <SelectItem key={val} value={val}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Submit */}
            <Button
              type="submit"
              className="w-full rounded-xl h-12 text-base gap-2"
              disabled={!canContinue || isSaving}
            >
              {isSaving ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving…</>
              ) : (
                <>Continue — gather company knowledge <ArrowRight className="w-4 h-4 ml-2" /></>
              )}
            </Button>

            <p className="text-center text-xs text-muted-foreground">
              <Sparkles className="inline w-3 h-3 mr-1" />
              Your company's website will be scraped in the background as you continue setting up your agent.
            </p>
          </>
        )}

      </form>
    </div>
  )
}
