"use client"

import React, { useState } from 'react'
import { ChevronRight, ChevronLeft, Check, X } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { AgentCreationStep } from "./steps/agent-creation-step"
import { KnowledgeUploadStep } from "./steps/knowledge-upload-step"
import { VoicePersonalityStep } from "./steps/voice-personality-step"
import { ChannelSetupStep } from "./steps/channel-setup-step"

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
}

export function OnboardingWizard({ open, onOpenChange, onComplete }: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [formData, setFormData] = useState<Record<string, any>>({})

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCompletedSteps(prev => [...prev, currentStep])
      setCurrentStep(currentStep + 1)
    } else {
      // Complete agent creation
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
    // Mock agent creation - simulate API call
    setTimeout(() => {
      onComplete()
      onOpenChange(false)
      // Reset wizard state
      setCurrentStep(0)
      setCompletedSteps([])
      setFormData({})
    }, 1000)
  }

  const CurrentStepComponent = steps[currentStep].component

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-4xl h-[95vh] max-h-[900px] overflow-hidden p-0">
        <DialogHeader className="border-b pb-4 px-4 sm:px-6">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl sm:text-2xl font-bold">Setup Your AI Agent</DialogTitle>
            <div className="flex items-center space-x-2 sm:space-x-4">
              <div className="text-xs sm:text-sm text-muted-foreground">
                Step {currentStep + 1} of {steps.length}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Progress Steps */}
          <div className="pt-4">
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
            <div className="hidden sm:flex items-center space-x-4 overflow-x-auto">
              {steps.map((step, index) => (
                <React.Fragment key={step.id}>
                  <div className="flex items-center space-x-3 flex-shrink-0">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                        index < currentStep || completedSteps.includes(index)
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
                        className={`font-medium ${
                          index <= currentStep ? 'text-foreground' : 'text-muted-foreground'
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
        </DialogHeader>

        {/* Step Content */}
        <div className="overflow-y-auto flex-1 px-4 sm:px-6 py-4 sm:py-6">
          <CurrentStepComponent
            data={formData}
            onDataChange={handleStepData}
            onNext={handleNext}
            onPrevious={handlePrevious}
            canGoNext={true}
            canGoPrevious={currentStep > 0}
          />
        </div>

        {/* Navigation */}
        <div className="border-t pt-3 sm:pt-4 pb-2 px-4 sm:px-6">
          <div className="flex items-center justify-between gap-3">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={currentStep === 0}
              className="flex-1 sm:flex-none"
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>
            
            <Button 
              onClick={handleNext}
              className="flex-1 sm:flex-none"
            >
              {currentStep === steps.length - 1 ? 'Complete Setup' : 'Continue'}
              {currentStep < steps.length - 1 && <ChevronRight className="h-4 w-4 ml-2" />}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}