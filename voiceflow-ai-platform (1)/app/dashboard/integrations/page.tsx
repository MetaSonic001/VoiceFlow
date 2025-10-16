"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import {
  Zap,
  Settings,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Key,
  Webhook,
  Database,
  Mail,
  MessageSquare,
  Phone,
  Calendar,
  Cloud,
  Shield,
  Plus
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Integration {
  id: string
  name: string
  description: string
  category: 'communication' | 'storage' | 'analytics' | 'payment' | 'ai' | 'other'
  status: 'connected' | 'disconnected' | 'error' | 'configuring'
  icon: string
  configuredAt?: string
  lastSync?: string
  errorMessage?: string
  settings: {
    apiKey?: string
    webhookUrl?: string
    apiEndpoint?: string
    credentials?: Record<string, string>
  }
}

interface IntegrationTemplate {
  id: string
  name: string
  description: string
  category: string
  icon: string
  requiredFields: string[]
  documentationUrl: string
}

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [templates, setTemplates] = useState<IntegrationTemplate[]>([])
  const [showAddIntegration, setShowAddIntegration] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<IntegrationTemplate | null>(null)
  const [configForm, setConfigForm] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [testingConnection, setTestingConnection] = useState<string | null>(null)

  useEffect(() => {
    loadIntegrations()
    loadTemplates()
  }, [])

  const loadIntegrations = async () => {
    try {
      setLoading(true)
      // This would call integrations API endpoints
      // const data = await apiClient.getIntegrations()

      // Mock data for now
      const mockIntegrations: Integration[] = [
        {
          id: 'twilio',
          name: 'Twilio',
          description: 'Voice and SMS communication platform',
          category: 'communication',
          status: 'connected',
          icon: 'Phone',
          configuredAt: '2024-01-01T10:00:00Z',
          lastSync: '2024-01-15T14:30:00Z',
          settings: {
            apiKey: 'SK****************************',
            apiEndpoint: 'https://api.twilio.com'
          }
        },
        {
          id: 'openai',
          name: 'OpenAI',
          description: 'AI language models and embeddings',
          category: 'ai',
          status: 'connected',
          icon: 'Zap',
          configuredAt: '2024-01-01T10:00:00Z',
          lastSync: '2024-01-15T14:25:00Z',
          settings: {
            apiKey: 'sk-****************************'
          }
        },
        {
          id: 'stripe',
          name: 'Stripe',
          description: 'Payment processing and billing',
          category: 'payment',
          status: 'error',
          icon: 'CreditCard',
          configuredAt: '2024-01-01T10:00:00Z',
          lastSync: '2024-01-15T12:00:00Z',
          errorMessage: 'Invalid API key',
          settings: {
            apiKey: 'sk_test_****************************'
          }
        },
        {
          id: 'slack',
          name: 'Slack',
          description: 'Team communication and notifications',
          category: 'communication',
          status: 'disconnected',
          icon: 'MessageSquare',
          settings: {}
        },
        {
          id: 'google-drive',
          name: 'Google Drive',
          description: 'Cloud storage and file management',
          category: 'storage',
          status: 'configuring',
          icon: 'Cloud',
          settings: {}
        }
      ]
      setIntegrations(mockIntegrations)
    } catch (error) {
      console.error('Failed to load integrations:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTemplates = async () => {
    try {
      // This would call integration templates API endpoint
      // const data = await apiClient.getIntegrationTemplates()

      // Mock data for now
      const mockTemplates: IntegrationTemplate[] = [
        {
          id: 'discord',
          name: 'Discord',
          description: 'Connect Discord for community management and notifications',
          category: 'communication',
          icon: 'MessageSquare',
          requiredFields: ['botToken', 'serverId'],
          documentationUrl: 'https://discord.com/developers/docs'
        },
        {
          id: 'notion',
          name: 'Notion',
          description: 'Sync documents and knowledge bases with Notion',
          category: 'storage',
          icon: 'FileText',
          requiredFields: ['apiKey', 'workspaceId'],
          documentationUrl: 'https://developers.notion.com'
        },
        {
          id: 'sendgrid',
          name: 'SendGrid',
          description: 'Email delivery and marketing automation',
          category: 'communication',
          icon: 'Mail',
          requiredFields: ['apiKey'],
          documentationUrl: 'https://docs.sendgrid.com'
        },
        {
          id: 'zoom',
          name: 'Zoom',
          description: 'Video conferencing and meeting integration',
          category: 'communication',
          icon: 'Video',
          requiredFields: ['clientId', 'clientSecret', 'webhookUrl'],
          documentationUrl: 'https://marketplace.zoom.us/docs/api-reference'
        },
        {
          id: 'dropbox',
          name: 'Dropbox',
          description: 'File storage and collaboration',
          category: 'storage',
          icon: 'Cloud',
          requiredFields: ['accessToken'],
          documentationUrl: 'https://www.dropbox.com/developers/documentation'
        }
      ]
      setTemplates(mockTemplates)
    } catch (error) {
      console.error('Failed to load integration templates:', error)
    }
  }

  const testConnection = async (integrationId: string) => {
    try {
      setTestingConnection(integrationId)
      // This would call a test connection API endpoint
      // await apiClient.testIntegrationConnection(integrationId)

      // Simulate testing delay
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Update integration status
      setIntegrations(prev =>
        prev.map(integration =>
          integration.id === integrationId
            ? { ...integration, status: 'connected' as const, lastSync: new Date().toISOString() }
            : integration
        )
      )
    } catch (error) {
      console.error('Failed to test connection:', error)
      setIntegrations(prev =>
        prev.map(integration =>
          integration.id === integrationId
            ? { ...integration, status: 'error' as const, errorMessage: 'Connection test failed' }
            : integration
        )
      )
    } finally {
      setTestingConnection(null)
    }
  }

  const toggleIntegration = async (integrationId: string, enabled: boolean) => {
    try {
      setIntegrations(prev =>
        prev.map(integration =>
          integration.id === integrationId
            ? { ...integration, status: enabled ? 'connected' : 'disconnected' }
            : integration
        )
      )
      // This would call an update integration API endpoint
      // await apiClient.updateIntegration(integrationId, { enabled })
    } catch (error) {
      console.error('Failed to toggle integration:', error)
    }
  }

  const configureIntegration = async (integrationId: string, settings: Record<string, string>) => {
    try {
      // This would call a configure integration API endpoint
      // await apiClient.configureIntegration(integrationId, settings)

      setIntegrations(prev =>
        prev.map(integration =>
          integration.id === integrationId
            ? {
                ...integration,
                status: 'connected',
                configuredAt: new Date().toISOString(),
                settings
              }
            : integration
        )
      )
      setShowAddIntegration(false)
      setSelectedTemplate(null)
      setConfigForm({})
    } catch (error) {
      console.error('Failed to configure integration:', error)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'disconnected': return <XCircle className="w-5 h-5 text-gray-500" />
      case 'error': return <AlertTriangle className="w-5 h-5 text-red-500" />
      case 'configuring': return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
      default: return <XCircle className="w-5 h-5 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'connected': return 'default'
      case 'disconnected': return 'secondary'
      case 'error': return 'destructive'
      case 'configuring': return 'outline'
      default: return 'outline'
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'communication': return <MessageSquare className="w-5 h-5" />
      case 'storage': return <Database className="w-5 h-5" />
      case 'analytics': return <BarChart3 className="w-5 h-5" />
      case 'payment': return <CreditCard className="w-5 h-5" />
      case 'ai': return <Zap className="w-5 h-5" />
      default: return <Settings className="w-5 h-5" />
    }
  }

  const getIconComponent = (iconName: string) => {
    switch (iconName) {
      case 'Phone': return <Phone className="w-6 h-6" />
      case 'Zap': return <Zap className="w-6 h-6" />
      case 'CreditCard': return <CreditCard className="w-6 h-6" />
      case 'MessageSquare': return <MessageSquare className="w-6 h-6" />
      case 'Cloud': return <Cloud className="w-6 h-6" />
      case 'Mail': return <Mail className="w-6 h-6" />
      case 'FileText': return <FileText className="w-6 h-6" />
      case 'Calendar': return <Calendar className="w-6 h-6" />
      default: return <Settings className="w-6 h-6" />
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex">
          <DashboardSidebar />
          <div className="flex-1 ml-64">
            <div className="p-6">
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                <span className="ml-2">Loading integrations...</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Integrations</h1>
                <p className="text-muted-foreground">Connect and manage third-party services</p>
              </div>
              <Dialog open={showAddIntegration} onOpenChange={setShowAddIntegration}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Integration
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Add New Integration</DialogTitle>
                    <DialogDescription>
                      Choose an integration to add to your workspace
                    </DialogDescription>
                  </DialogHeader>
                  {!selectedTemplate ? (
                    <div className="grid gap-4">
                      {templates.map((template) => (
                        <Card
                          key={template.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => setSelectedTemplate(template)}
                        >
                          <CardContent className="p-4">
                            <div className="flex items-center space-x-4">
                              {getIconComponent(template.icon)}
                              <div className="flex-1">
                                <h4 className="font-medium">{template.name}</h4>
                                <p className="text-sm text-muted-foreground">{template.description}</p>
                                <Badge variant="outline" className="mt-2">
                                  {template.category}
                                </Badge>
                              </div>
                              <ExternalLink className="w-4 h-4 text-muted-foreground" />
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-center space-x-4 p-4 bg-muted rounded-lg">
                        {getIconComponent(selectedTemplate.icon)}
                        <div>
                          <h4 className="font-medium">{selectedTemplate.name}</h4>
                          <p className="text-sm text-muted-foreground">{selectedTemplate.description}</p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <h4 className="font-medium">Configuration</h4>
                        {selectedTemplate.requiredFields.map((field) => (
                          <div key={field} className="space-y-2">
                            <Label htmlFor={field}>
                              {field.charAt(0).toUpperCase() + field.slice(1).replace(/([A-Z])/g, ' $1')}
                            </Label>
                            <Input
                              id={field}
                              type={field.includes('secret') || field.includes('key') || field.includes('token') ? 'password' : 'text'}
                              value={configForm[field] || ''}
                              onChange={(e) => setConfigForm(prev => ({ ...prev, [field]: e.target.value }))}
                              placeholder={`Enter your ${field}`}
                            />
                          </div>
                        ))}
                      </div>

                      <div className="flex justify-between">
                        <Button variant="outline" onClick={() => setSelectedTemplate(null)}>
                          Back
                        </Button>
                        <Button
                          onClick={() => configureIntegration(selectedTemplate.id, configForm)}
                          disabled={selectedTemplate.requiredFields.some(field => !configForm[field])}
                        >
                          Configure Integration
                        </Button>
                      </div>
                    </div>
                  )}
                </DialogContent>
              </Dialog>
            </div>

            {/* Integration Status Overview */}
            <div className="grid md:grid-cols-4 gap-6 mb-6">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Connected</p>
                      <p className="text-2xl font-bold text-green-600">
                        {integrations.filter(i => i.status === 'connected').length}
                      </p>
                    </div>
                    <CheckCircle className="w-8 h-8 text-green-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Disconnected</p>
                      <p className="text-2xl font-bold text-gray-600">
                        {integrations.filter(i => i.status === 'disconnected').length}
                      </p>
                    </div>
                    <XCircle className="w-8 h-8 text-gray-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Errors</p>
                      <p className="text-2xl font-bold text-red-600">
                        {integrations.filter(i => i.status === 'error').length}
                      </p>
                    </div>
                    <AlertTriangle className="w-8 h-8 text-red-500" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Configuring</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {integrations.filter(i => i.status === 'configuring').length}
                      </p>
                    </div>
                    <RefreshCw className="w-8 h-8 text-blue-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Integrations List */}
            <Card>
              <CardHeader>
                <CardTitle>Connected Services</CardTitle>
                <CardDescription>Manage your integrated services and their configurations</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {integrations.map((integration) => (
                    <div key={integration.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className="p-2 bg-muted rounded-lg">
                          {getIconComponent(integration.icon)}
                        </div>
                        <div>
                          <h4 className="font-medium">{integration.name}</h4>
                          <p className="text-sm text-muted-foreground">{integration.description}</p>
                          <div className="flex items-center space-x-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {integration.category}
                            </Badge>
                            {integration.lastSync && (
                              <span className="text-xs text-muted-foreground">
                                Last sync: {new Date(integration.lastSync).toLocaleString()}
                              </span>
                            )}
                          </div>
                          {integration.errorMessage && (
                            <p className="text-xs text-red-600 mt-1">{integration.errorMessage}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <Badge variant={getStatusBadgeVariant(integration.status)}>
                          {integration.status}
                        </Badge>
                        <div className="flex space-x-2">
                          {integration.status === 'connected' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => testConnection(integration.id)}
                              disabled={testingConnection === integration.id}
                            >
                              {testingConnection === integration.id ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <RefreshCw className="w-4 h-4" />
                              )}
                            </Button>
                          )}
                          <Switch
                            checked={integration.status === 'connected'}
                            onCheckedChange={(checked) => toggleIntegration(integration.id, checked)}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}