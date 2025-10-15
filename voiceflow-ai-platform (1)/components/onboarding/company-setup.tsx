"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { useToast } from '@/hooks/use-toast'
import { Button } from "@/components/ui/button"
import MotionWrapper from '@/components/ui/MotionWrapper'
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Building2 } from "lucide-react"

interface CompanySetupProps {
  onComplete: (data: any) => void
}

export function CompanySetup({ onComplete }: CompanySetupProps) {
  const [formData, setFormData] = useState({
    companyName: "",
    industry: "",
    useCase: "",
    description: "",
  })
  const { toast } = useToast()

  useEffect(() => {
    ;(async () => {
      try {
        const prog = await (await import('@/lib/api-client')).apiClient.getOnboardingProgress()
        if (prog?.exists && prog.data?.company) setFormData(prog.data.company)
      } catch (e) {
        // ignore
      }
    })()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    ;(async () => {
      try {
        await (await import('@/lib/api-client')).apiClient.saveCompanyProfile({ name: formData.companyName, industry: formData.industry, useCase: formData.useCase })
        try { await (await import('@/lib/api-client')).apiClient.saveOnboardingProgress({ current_step: 1, data: { company: formData } }) } catch (e) {}
        toast({ title: 'Saved', description: 'Company profile saved' })
      } catch (e) {
        toast({ title: 'Save failed', description: 'Failed to persist company profile' })
      }
      onComplete({ company: formData })
    })()
  }

  return (
    <MotionWrapper>
      <div className="space-y-6">
      <div className="text-center">
        <Building2 className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Tell us about your company</h2>
        <p className="text-muted-foreground">
          This helps us customize your AI agent to better serve your business needs.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="companyName">Company Name *</Label>
          <Input
            id="companyName"
            placeholder="Acme Corporation"
            value={formData.companyName}
            onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="industry">Industry *</Label>
          <Select value={formData.industry} onValueChange={(value) => setFormData({ ...formData, industry: value })}>
            <SelectTrigger>
              <SelectValue placeholder="Select your industry" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="technology">Technology</SelectItem>
              <SelectItem value="healthcare">Healthcare</SelectItem>
              <SelectItem value="finance">Finance</SelectItem>
              <SelectItem value="retail">Retail</SelectItem>
              <SelectItem value="education">Education</SelectItem>
              <SelectItem value="real-estate">Real Estate</SelectItem>
              <SelectItem value="consulting">Consulting</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="useCase">Primary Use Case *</Label>
          <Select value={formData.useCase} onValueChange={(value) => setFormData({ ...formData, useCase: value })}>
            <SelectTrigger>
              <SelectValue placeholder="What will your agent primarily handle?" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="customer-support">Customer Support</SelectItem>
              <SelectItem value="sales-lead-qualification">Sales & Lead Qualification</SelectItem>
              <SelectItem value="appointment-scheduling">Appointment Scheduling</SelectItem>
              <SelectItem value="hr-internal-helpdesk">HR & Internal Helpdesk</SelectItem>
              <SelectItem value="order-status-tracking">Order Status & Tracking</SelectItem>
              <SelectItem value="general-inquiries">General Business Inquiries</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Brief Description (Optional)</Label>
          <Textarea
            id="description"
            placeholder="Tell us more about your business and what you hope to achieve with AI agents..."
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
          />
        </div>

        <Button
          type="submit"
          className="w-full"
          disabled={!formData.companyName || !formData.industry || !formData.useCase}
        >
          Continue to Agent Creation
        </Button>
      </form>
      </div>
    </MotionWrapper>
  )
}
