"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { AlertCircle, CheckCircle, Key, Shield, Bell, Database, Zap, Globe } from "lucide-react"
import { apiClient } from "@/lib/api-client"

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    notifications: {
      emailAlerts: true,
      pushNotifications: false,
      weeklyReports: true,
      errorAlerts: true
    },
    security: {
      twoFactorAuth: false,
      sessionTimeout: 30,
      passwordPolicy: 'strong'
    },
    integrations: {
      twilioEnabled: true,
      webhookUrl: '',
      apiRateLimit: 100
    },
    system: {
      maintenanceMode: false,
      debugMode: false,
      logLevel: 'info'
    }
  })

  type ApiKey = {
    id: string
    name: string
    key: string
    created: string
    lastUsed: string | null
    permissions: string[]
  }

  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadSettings()
    loadApiKeys()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await apiClient.getSettings()
      setSettings(data)
    } catch (error) {
      console.error('Failed to load settings:', error)
      // Keep default settings
    }
  }

  const loadApiKeys = async () => {
    try {
      // For now, using mock data since API doesn't exist yet
      const mockApiKeys: ApiKey[] = [
        {
          id: 'key-1',
          name: 'Production API Key',
          key: 'sk_prod_******************************',
          created: '2024-01-01T00:00:00Z',
          lastUsed: '2024-01-15T10:30:00Z',
          permissions: ['read', 'write', 'admin']
        },
        {
          id: 'key-2',
          name: 'Development API Key',
          key: 'sk_dev_*******************************',
          created: '2024-01-05T00:00:00Z',
          lastUsed: '2024-01-14T15:45:00Z',
          permissions: ['read', 'write']
        }
      ]
      setApiKeys(mockApiKeys)
    } catch (error) {
      console.error('Failed to load API keys:', error)
    }
  }

  const updateSettings = async (category: string, updates: any) => {
    setLoading(true)
    try {
      await apiClient.updateSettings({ [category]: updates })
      setSettings(prev => ({
        ...prev,
        [category]: { ...prev[category as keyof typeof prev], ...updates }
      }))
      setMessage('Settings updated successfully!')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      console.error('Failed to update settings:', error)
      setMessage('Failed to update settings')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const generateApiKey = async () => {
    setLoading(true)
    try {
      // This would call an API key generation endpoint
      // const newKey = await apiClient.generateApiKey()
      const newKey = {
        id: Date.now().toString(),
        name: 'New API Key',
        key: `vk_${Math.random().toString(36).substring(2, 15)}`,
        created: new Date().toISOString(),
        lastUsed: null,
        permissions: ['read', 'write']
      }
      setApiKeys(prev => [...prev, newKey])
      setMessage('API key generated successfully!')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage('Failed to generate API key')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  const deleteApiKey = async (keyId: string) => {
    try {
      // This would call an API key deletion endpoint
      // await apiClient.deleteApiKey(keyId)
      setApiKeys(prev => prev.filter(key => key.id !== keyId))
      setMessage('API key deleted successfully!')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage('Failed to delete API key')
      setTimeout(() => setMessage(''), 3000)
    }
  }

  return (
    <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Settings</h1>
                <p className="text-muted-foreground">Manage your account and system preferences</p>
              </div>
            </div>

            {message && (
              <div className={`mb-4 p-4 rounded-lg ${message.includes('success') ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                {message.includes('success') ? <CheckCircle className="w-5 h-5 inline mr-2" /> : <AlertCircle className="w-5 h-5 inline mr-2" />}
                {message}
              </div>
            )}

            <Tabs defaultValue="general" className="space-y-6">
              <TabsList className="grid w-full grid-cols-5">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="security">Security</TabsTrigger>
                <TabsTrigger value="integrations">Integrations</TabsTrigger>
                <TabsTrigger value="api-keys">API Keys</TabsTrigger>
                <TabsTrigger value="system">System</TabsTrigger>
              </TabsList>

              <TabsContent value="general" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Bell className="w-5 h-5" />
                      <span>Notifications</span>
                    </CardTitle>
                    <CardDescription>Configure how you receive notifications and alerts</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Email Alerts</Label>
                        <p className="text-sm text-muted-foreground">Receive email notifications for important events</p>
                      </div>
                      <Switch
                        checked={settings.notifications.emailAlerts}
                        onCheckedChange={(checked) => updateSettings('notifications', { emailAlerts: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Push Notifications</Label>
                        <p className="text-sm text-muted-foreground">Receive push notifications in your browser</p>
                      </div>
                      <Switch
                        checked={settings.notifications.pushNotifications}
                        onCheckedChange={(checked) => updateSettings('notifications', { pushNotifications: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Weekly Reports</Label>
                        <p className="text-sm text-muted-foreground">Receive weekly performance reports</p>
                      </div>
                      <Switch
                        checked={settings.notifications.weeklyReports}
                        onCheckedChange={(checked) => updateSettings('notifications', { weeklyReports: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Error Alerts</Label>
                        <p className="text-sm text-muted-foreground">Get notified when errors occur</p>
                      </div>
                      <Switch
                        checked={settings.notifications.errorAlerts}
                        onCheckedChange={(checked) => updateSettings('notifications', { errorAlerts: checked })}
                      />
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="security" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Shield className="w-5 h-5" />
                      <span>Security Settings</span>
                    </CardTitle>
                    <CardDescription>Manage security preferences and authentication</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Two-Factor Authentication</Label>
                        <p className="text-sm text-muted-foreground">Add an extra layer of security to your account</p>
                      </div>
                      <Switch
                        checked={settings.security.twoFactorAuth}
                        onCheckedChange={(checked) => updateSettings('security', { twoFactorAuth: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <Label>Session Timeout (minutes)</Label>
                      <Select
                        value={settings.security.sessionTimeout.toString()}
                        onValueChange={(value) => updateSettings('security', { sessionTimeout: parseInt(value) })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="15">15 minutes</SelectItem>
                          <SelectItem value="30">30 minutes</SelectItem>
                          <SelectItem value="60">1 hour</SelectItem>
                          <SelectItem value="240">4 hours</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <Label>Password Policy</Label>
                      <Select
                        value={settings.security.passwordPolicy}
                        onValueChange={(value) => updateSettings('security', { passwordPolicy: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="basic">Basic (8+ characters)</SelectItem>
                          <SelectItem value="strong">Strong (12+ chars, mixed case, numbers)</SelectItem>
                          <SelectItem value="complex">Complex (16+ chars, special chars)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="integrations" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Globe className="w-5 h-5" />
                      <span>Third-party Integrations</span>
                    </CardTitle>
                    <CardDescription>Connect with external services and APIs</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Twilio Integration</Label>
                        <p className="text-sm text-muted-foreground">Enable phone and SMS capabilities</p>
                      </div>
                      <Switch
                        checked={settings.integrations.twilioEnabled}
                        onCheckedChange={(checked) => updateSettings('integrations', { twilioEnabled: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <Label>Webhook URL</Label>
                      <Input
                        value={settings.integrations.webhookUrl}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          integrations: { ...prev.integrations, webhookUrl: e.target.value }
                        }))}
                        placeholder="https://your-app.com/webhook"
                      />
                      <p className="text-sm text-muted-foreground">URL to receive webhook notifications</p>
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <Label>API Rate Limit (requests/minute)</Label>
                      <Input
                        type="number"
                        value={settings.integrations.apiRateLimit}
                        onChange={(e) => setSettings(prev => ({
                          ...prev,
                          integrations: { ...prev.integrations, apiRateLimit: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="api-keys" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Key className="w-5 h-5" />
                      <span>API Keys</span>
                    </CardTitle>
                    <CardDescription>Manage API keys for external access</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <Button onClick={generateApiKey} disabled={loading}>
                      Generate New API Key
                    </Button>
                    <div className="space-y-2">
                      {apiKeys.map((key: any) => (
                        <div key={key.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="space-y-1">
                            <p className="font-medium">{key.name}</p>
                            <p className="text-sm text-muted-foreground font-mono">{key.key}</p>
                            <p className="text-xs text-muted-foreground">
                              Created: {new Date(key.created).toLocaleDateString()}
                              {key.lastUsed && ` • Last used: ${new Date(key.lastUsed).toLocaleDateString()}`}
                            </p>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Badge variant="secondary">{key.permissions.join(', ')}</Badge>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => deleteApiKey(key.id)}
                            >
                              Delete
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="system" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Database className="w-5 h-5" />
                      <span>System Settings</span>
                    </CardTitle>
                    <CardDescription>Advanced system configuration (Admin only)</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Maintenance Mode</Label>
                        <p className="text-sm text-muted-foreground">Temporarily disable the system for maintenance</p>
                      </div>
                      <Switch
                        checked={settings.system.maintenanceMode}
                        onCheckedChange={(checked) => updateSettings('system', { maintenanceMode: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Debug Mode</Label>
                        <p className="text-sm text-muted-foreground">Enable detailed logging and error reporting</p>
                      </div>
                      <Switch
                        checked={settings.system.debugMode}
                        onCheckedChange={(checked) => updateSettings('system', { debugMode: checked })}
                      />
                    </div>
                    <Separator />
                    <div className="space-y-2">
                      <Label>Log Level</Label>
                      <Select
                        value={settings.system.logLevel}
                        onValueChange={(value) => updateSettings('system', { logLevel: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="error">Error</SelectItem>
                          <SelectItem value="warn">Warning</SelectItem>
                          <SelectItem value="info">Info</SelectItem>
                          <SelectItem value="debug">Debug</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>
        
      )
    }