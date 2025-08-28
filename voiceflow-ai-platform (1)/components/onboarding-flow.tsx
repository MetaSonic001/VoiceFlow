"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { CompanySetup } from "@/components/onboarding/company-setup"
import { AgentCreation } from "@/components/onboarding/agent-creation"
import { KnowledgeUpload } from "@/components/onboarding/knowledge-upload"
import { VoicePersonality } from "@/components/onboarding/voice-personality"
import { ChannelSetup } from "@/components/onboarding/channel-setup"
import { TestingSandbox } from "@/components/onboarding/testing-sandbox"
import { GoLive } from "@/components/onboarding/go-live"
import { Brain, CheckCircle } from "lucide-react"
import { useRouter } from "next/navigation"

const STEPS = [
  { id: 1, title: "Company Profile", description: "Tell us about your business" },
  { id: 2, title: "Agent Creation", description: "Create your first AI agent" },
  { id: 3, title: "Knowledge Upload", description: "Upload your documents and FAQs" },
  { id: 4, title: "Voice & Personality", description: "Choose voice and tone" },
  { id: 5, title: "Channel Setup", description: "Configure communication channels" },
  { id: 6, title: "Testing", description: "Test your agent before going live" },
  { id: 7, title: "Go Live", description: "Deploy your agent" },
]

export function OnboardingFlow() {
  const [currentStep, setCurrentStep] = useState(1)
  const [completedSteps, setCompletedSteps] = useState<number[]>([])
  const [onboardingData, setOnboardingData] = useState({})
  const router = useRouter()

  const progress = ((currentStep - 1) / (STEPS.length - 1)) * 100

  const handleStepComplete = (stepData: any) => {
    setOnboardingData((prev) => ({ ...prev, ...stepData }))
    setCompletedSteps((prev) => [...prev, currentStep])

    if (currentStep < STEPS.length) {
      setCurrentStep(currentStep + 1)
    } else {
      // Onboarding complete, redirect to dashboard
      router.push("/dashboard")
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return <CompanySetup onComplete={handleStepComplete} />
      case 2:
        return <AgentCreation onComplete={handleStepComplete} />
      case 3:
        return <KnowledgeUpload onComplete={handleStepComplete} />
      case 4:
        return <VoicePersonality onComplete={handleStepComplete} />
      case 5:
        return <ChannelSetup onComplete={handleStepComplete} />
      case 6:
        return <TestingSandbox onComplete={handleStepComplete} />
      case 7:
        return <GoLive onComplete={handleStepComplete} />
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/95 backdrop-blur">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">VoiceFlow AI</span>
          </div>
          <Badge variant="secondary">Setup in Progress</Badge>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Progress Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold">Agent Setup</h1>
              <p className="text-muted-foreground">
                Step {currentStep} of {STEPS.length}: {STEPS[currentStep - 1]?.title}
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground mb-1">Progress</div>
              <div className="text-2xl font-bold">{Math.round(progress)}%</div>
            </div>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        <div className="grid lg:grid-cols-4 gap-8">
          {/* Steps Sidebar */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Setup Steps</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {STEPS.map((step) => (
                  <div
                    key={step.id}
                    className={`flex items-center space-x-3 p-2 rounded-lg transition-colors ${
                      step.id === currentStep
                        ? "bg-accent text-accent-foreground"
                        : completedSteps.includes(step.id)
                          ? "bg-muted text-muted-foreground"
                          : "text-muted-foreground"
                    }`}
                  >
                    {completedSteps.includes(step.id) ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : (
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs ${
                          step.id === currentStep ? "border-accent-foreground bg-accent-foreground text-accent" : ""
                        }`}
                      >
                        {step.id === currentStep ? step.id : step.id}
                      </div>
                    )}
                    <div>
                      <div className="font-medium text-sm">{step.title}</div>
                      <div className="text-xs opacity-70">{step.description}</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <Card>
              <CardContent className="p-6">{renderStepContent()}</CardContent>
            </Card>

            {/* Navigation */}
            <div className="flex justify-between mt-6">
              <Button variant="outline" onClick={handleBack} disabled={currentStep === 1}>
                Back
              </Button>
              <div className="text-sm text-muted-foreground">
                Need help?{" "}
                <a href="#" className="text-accent hover:underline">
                  Contact Support
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
