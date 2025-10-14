"use client"

import React, { useState, useEffect } from 'react'
import { ChevronRight, ChevronLeft, Check, X } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { AgentCreationStep } from "./steps/agent-creation-step"
import { KnowledgeUploadStep } from "./steps/knowledge-upload-step"
import { VoicePersonalityStep } from "./steps/voice-personality-step"
import { ChannelSetupStep } from "./steps/channel-setup-step"
import { AnimatePresence } from 'framer-motion'

const steps = [
  { id: 'agent', title: 'Create Agent', component: AgentCreationStep },
  { id: 'knowledge', title: 'Upload Knowledge', component: KnowledgeUploadStep },
  { id: 'voice', title: 'Voice & Personality', component: VoicePersonalityStep },
  { id: 'channels', title: 'Setup Channels', component: ChannelSetupStep },
]

interface OnboardingWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete: () => void
  startStep?: number
}

export function OnboardingWizard({ open, onOpenChange, onComplete, startStep }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [serverProgress, setServerProgress] = useState<Record<string, any> | null>(null)

  useEffect(() => {
    if (open && typeof startStep === 'number' && !isNaN(startStep)) {
      const idx = Math.max(0, Math.min(steps.length - 1, startStep - 1))
      setCurrentStep(idx)
    }
  }, [open, startStep])

  useEffect(() => {
    let mounted = true
    if (!open) return
      ; (async () => {
        try {
          const res = await (await import('@/lib/api-client')).apiClient.getOnboardingProgress()
          if (mounted && res && res.exists) {
            setServerProgress(res.data || {})
            setFormData(res.data || {})
            if (res.current_step && typeof res.current_step === 'number') {
              const idx = Math.max(0, Math.min(steps.length - 1, res.current_step - 1))
              setCurrentStep(idx)
            }
          }
        } catch (e) {
          console.warn('No onboarding progress available', e)
        }
      })()
    return () => { mounted = false }
  }, [open])

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCompletedSteps(prev => [...prev, currentStep])
      setCurrentStep(currentStep + 1)
    } else {
      handleComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleStepData = (stepData: Record<string, any>) => {
    setFormData(prev => ({ ...prev, ...stepData }))
  }

  const handleComplete = () => {
    setTimeout(() => {
      onComplete()
      onOpenChange(false)
      setCurrentStep(0)
      setCompletedSteps([])
      setFormData({})
    }, 1000)
  }

  const CurrentStepComponent = steps[currentStep].component

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="w-full max-w-5xl h-full overflow-scroll p-0 gap-0"
        style={{
          height: '90vh',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header - Fixed */}
        <div
          className="border-b px-4 sm:px-6 py-4"
          style={{ flexShrink: 0 }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl sm:text-2xl font-bold">Setup Your AI Agent</h2>
          </div>

          {/* Mobile Progress Bar */}
          <div className="sm:hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-foreground">
                {steps[currentStep].title}
              </span>
              <span className="text-xs text-muted-foreground">
                {currentStep + 1}/{steps.length}
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
              />
            </div>
          </div>

          {/* Desktop Progress Steps */}
          <div className="hidden sm:flex items-center gap-4 overflow-x-auto pb-1">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-200 ${index < currentStep || completedSteps.includes(index)
                      ? 'bg-primary text-primary-foreground'
                      : index === currentStep
                        ? 'bg-primary/10 text-primary border-2 border-primary'
                        : 'bg-muted text-muted-foreground'
                      }`}
                  >
                    {completedSteps.includes(index) ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <div className="text-sm">
                    <div
                      className={`font-medium whitespace-nowrap ${index <= currentStep ? 'text-foreground' : 'text-muted-foreground'
                        }`}
                    >
                      {step.title}
                    </div>
                  </div>
                </div>
                {index < steps.length - 1 && (
                  <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Step Content - Scrollable Area */}
        <div
          className="px-4 sm:px-6 py-6 mix-h-screen overflow-scroll"
          style={{
            flex: 1,
            overflowY: 'scroll',
            minHeight: 0
          }}
        >
          <AnimatePresence mode="wait">
            <CurrentStepComponent
              key={currentStep}
              data={formData}
              initialData={serverProgress || undefined}
              onDataChange={handleStepData}
              onNext={handleNext}
              onPrevious={handlePrevious}
              canGoNext={true}
              canGoPrevious={currentStep > 0}
            />
          </AnimatePresence>
        </div>

        {/* Navigation Footer - Fixed at Bottom */}
        <div
          className="border-t bg-background px-4 sm:px-6 py-4"
          style={{
            flexShrink: 0,
            zIndex: 10
          }}
        >
          <div className="flex items-center justify-between gap-4">
            <Button
              onClick={handlePrevious}
              disabled={currentStep === 0}
              variant="outline"
              size="lg"
              className="min-w-[100px] sm:min-w-[120px]"
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>

            <Button
              onClick={handleNext}
              size="lg"
              className="min-w-[100px] sm:min-w-[120px] bg-primary hover:bg-primary/90"
            >
              {currentStep === steps.length - 1 ? 'Complete' : 'Continue'}
              {currentStep < steps.length - 1 && <ChevronRight className="h-4 w-4 ml-2" />}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

