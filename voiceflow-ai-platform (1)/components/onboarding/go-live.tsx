"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, Rocket, Phone, MessageSquare, Copy, ExternalLink } from "lucide-react"
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/use-toast'

interface GoLiveProps {
  onComplete: (data: any) => void
  phoneNumber?: string
}

export function GoLive({ onComplete, phoneNumber }: GoLiveProps) {
  const [isDeploying, setIsDeploying] = useState(false)
  const [isDeployed, setIsDeployed] = useState(false)
  const [deployedNumber, setDeployedNumber] = useState<string | undefined>(phoneNumber)
  const { toast } = useToast()

  useEffect(() => { setDeployedNumber(phoneNumber) }, [phoneNumber])

  const handleDeploy = async () => {
    setIsDeploying(true)
    try {
      // call backend deploy; fetch agent_id from server-side onboarding progress if needed
      let agentId: string | undefined = undefined
      try {
        const prog = await (await import('@/lib/api-client')).apiClient.getOnboardingProgress()
        if (prog?.exists && prog.agent_id) agentId = String(prog.agent_id)
      } catch (e) {
        // ignore
      }
      if (!agentId) throw new Error('Missing agent id')
      const res = await apiClient.deployAgent(agentId)
      toast({ title: 'Deployment started', description: 'Agent deployment is in progress' })
      setIsDeploying(false)
      setIsDeployed(true)
      if (res?.phone_number) setDeployedNumber(res.phone_number)

      // start polling status briefly
      const poll = async () => {
        try {
          const status = await apiClient.getDeploymentStatus(agentId)
          if (status?.status === 'ready' && status.message) {
            toast({ title: 'Deployment complete', description: status.message })
          }
        } catch (e) {
          // ignore
        }
      }
      setTimeout(poll, 2000)
    } catch (e: any) {
      setIsDeploying(false)
      toast({ title: 'Deployment failed', description: e?.message || 'Failed to deploy' })
    }
  }

  const handleComplete = () => {
    // Pass deployed info back to parent so it can persist and redirect
    onComplete({ deployed: isDeployed, phone_number: deployedNumber })
  }

  const copyPhoneNumber = () => {
    navigator.clipboard.writeText(deployedNumber || phoneNumber || "+1 (555) 123-4567")
  }

  const copyWidgetCode = () => {
    const widgetCode = `<script src="https://voiceflow-ai.com/widget.js" data-agent-id="agent-12345"></script>`
    navigator.clipboard.writeText(widgetCode)
  }

  if (!isDeployed) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <Rocket className="w-12 h-12 text-accent mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Ready to go live!</h2>
          <p className="text-muted-foreground">
            Your AI agent is configured and tested. Click deploy to make it available to your customers.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Deployment Summary</CardTitle>
            <CardDescription>Review your agent configuration before going live</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h4 className="font-medium">Agent Details</h4>
                <div className="text-sm space-y-1">
                  <p>
                    <span className="text-muted-foreground">Name:</span> Customer Support Assistant
                  </p>
                  <p>
                    <span className="text-muted-foreground">Voice:</span> Sarah (Professional Female)
                  </p>
                  <p>
                    <span className="text-muted-foreground">Tone:</span> Friendly & Professional
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium">Channels</h4>
                <div className="space-y-1">
                  <Badge variant="secondary">Phone: {deployedNumber || phoneNumber || "+1 (555) 123-4567"}</Badge>
                  <Badge variant="secondary">Website Chat Widget</Badge>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium">Knowledge Base</h4>
              <div className="text-sm text-muted-foreground">
                <p>• 3 documents uploaded</p>
                <p>• 1 website crawled</p>
                <p>• FAQ content added</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center">
          <Button onClick={handleDeploy} disabled={isDeploying} size="lg" className="px-8">
            {isDeploying ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                Deploying Agent...
              </>
            ) : (
              <>
                <Rocket className="w-4 h-4 mr-2" />
                Deploy Agent
              </>
            )}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Your agent is live!</h2>
        <p className="text-muted-foreground">
          Congratulations! Your AI agent is now active and ready to help your customers.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Phone className="w-5 h-5" />
              <span>Phone Access</span>
            </CardTitle>
            <CardDescription>Customers can call your agent</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
              <span className="font-mono">{phoneNumber || "+1 (555) 123-4567"}</span>
              <Button variant="ghost" size="sm" onClick={copyPhoneNumber}>
                <Copy className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Share this number with your customers or add it to your website.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="w-5 h-5" />
              <span>Website Widget</span>
            </CardTitle>
            <CardDescription>Add chat to your website</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 bg-muted rounded-lg">
              <code className="text-xs break-all">
                {`<script src="https://voiceflow-ai.com/widget.js" data-agent-id="agent-12345"></script>`}
              </code>
            </div>
            <div className="flex space-x-2">
              <Button variant="ghost" size="sm" onClick={copyWidgetCode}>
                <Copy className="w-4 h-4 mr-1" />
                Copy Code
              </Button>
              <Button variant="ghost" size="sm">
                <ExternalLink className="w-4 h-4 mr-1" />
                View Docs
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>What's Next?</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
            <div>
              <p className="font-medium">Monitor Performance</p>
              <p className="text-sm text-muted-foreground">
                Track calls, conversations, and customer satisfaction in your dashboard.
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
            <div>
              <p className="font-medium">Improve Over Time</p>
              <p className="text-sm text-muted-foreground">
                Review conversations and update your knowledge base to improve responses.
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
            <div>
              <p className="font-medium">Scale Your Operations</p>
              <p className="text-sm text-muted-foreground">
                Create additional agents for different departments or use cases.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-center">
        <Button onClick={handleComplete} size="lg" className="px-8">
          Go to Dashboard
        </Button>
      </div>
    </div>
  )
}
