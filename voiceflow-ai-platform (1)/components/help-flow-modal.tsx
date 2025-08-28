"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { UserPlus, Upload, Settings, TestTube, Rocket, ArrowRight, ArrowLeft, CheckCircle, Play } from "lucide-react"

interface HelpFlowModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function HelpFlowModal({ open, onOpenChange }: HelpFlowModalProps) {
  const [currentStep, setCurrentStep] = useState(0)

  const steps = [
    {
      icon: UserPlus,
      title: "Sign Up & Company Setup",
      description: "Create your account and set up your company profile",
      details: [
        "Enter your company details and industry",
        "Choose your primary use case (support, sales, HR)",
        "Set up team members and permissions",
        "Complete verification in under 2 minutes",
      ],
      time: "2 minutes",
    },
    {
      icon: Upload,
      title: "Upload Knowledge Base",
      description: "Add your documents, FAQs, and business information",
      details: [
        "Upload PDFs, Word docs, and text files",
        "Connect your website or knowledge base",
        "Add FAQs and common responses",
        "AI automatically processes and indexes content",
      ],
      time: "5 minutes",
    },
    {
      icon: Settings,
      title: "Configure Your Agent",
      description: "Customize voice, personality, and behavior",
      details: [
        "Choose from 50+ natural voices in multiple languages",
        "Set personality tone (professional, friendly, empathetic)",
        "Configure response patterns and escalation rules",
        "Set up integrations with your existing tools",
      ],
      time: "3 minutes",
    },
    {
      icon: TestTube,
      title: "Test & Refine",
      description: "Try your agent in our sandbox environment",
      details: [
        "Test conversations in real-time chat interface",
        "Make test calls to verify voice interactions",
        "Refine responses based on test results",
        "Ensure all scenarios work perfectly",
      ],
      time: "5 minutes",
    },
    {
      icon: Rocket,
      title: "Go Live",
      description: "Deploy your agent and start serving customers",
      details: [
        "Get your dedicated phone number instantly",
        "Embed chat widget on your website",
        "Connect WhatsApp and other channels",
        "Monitor performance with real-time analytics",
      ],
      time: "1 minute",
    },
  ]

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const totalTime = steps.reduce((acc, step) => {
    const minutes = Number.parseInt(step.time.split(" ")[0])
    return acc + minutes
  }, 0)

  const CurrentStepIcon = steps[currentStep].icon

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-center mb-2">How VoiceFlow AI Works</DialogTitle>
          <div className="text-center">
            <Badge variant="secondary" className="mb-4">
              <CheckCircle className="w-4 h-4 mr-2" />
              Complete setup in {totalTime} minutes
            </Badge>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Progress Bar */}
          <div className="flex items-center justify-between mb-8">
            {steps.map((_, index) => (
              <div key={index} className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                    index <= currentStep ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {index + 1}
                </div>
                {index < steps.length - 1 && (
                  <div className={`h-1 w-16 mx-2 transition-all ${index < currentStep ? "bg-primary" : "bg-muted"}`} />
                )}
              </div>
            ))}
          </div>

          {/* Current Step */}
          <Card className="border-2 border-primary/20">
            <CardHeader className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-r from-primary to-accent rounded-2xl flex items-center justify-center">
                <CurrentStepIcon className="w-8 h-8 text-white" />
              </div>
              <CardTitle className="text-2xl">{steps[currentStep].title}</CardTitle>
              <CardDescription className="text-lg">{steps[currentStep].description}</CardDescription>
              <Badge variant="outline" className="w-fit mx-auto">
                ⏱️ {steps[currentStep].time}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                {steps[currentStep].details.map((detail, index) => (
                  <div key={index} className="flex items-start space-x-3 p-3 bg-muted/50 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                    <span className="text-sm">{detail}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              onClick={prevStep}
              disabled={currentStep === 0}
              className="flex items-center bg-transparent"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Previous
            </Button>

            <div className="text-center">
              <div className="text-sm text-muted-foreground">
                Step {currentStep + 1} of {steps.length}
              </div>
            </div>

            {currentStep < steps.length - 1 ? (
              <Button onClick={nextStep} className="flex items-center">
                Next
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={() => onOpenChange(false)}
                className="flex items-center bg-gradient-to-r from-primary to-accent"
              >
                <Play className="w-4 h-4 mr-2" />
                Get Started Now
              </Button>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 pt-6 border-t">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">5 min</div>
              <div className="text-xs text-muted-foreground">Average Setup</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">99.9%</div>
              <div className="text-xs text-muted-foreground">Success Rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">24/7</div>
              <div className="text-xs text-muted-foreground">Support</div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
