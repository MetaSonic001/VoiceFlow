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
import { AlertCircle, CheckCircle, Key, Shield, Bell, Database, Zap, Globe, Loader2, ExternalLink, Trash2, Volume2, Brain } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { VoiceSelector } from "@/components/voice-selector"

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
    system: {
      maintenanceMode: false,
      debugMode: false,
      logLevel: 'info'
    }
  })

  // Twilio credentials state
  const [twilioAccountSid, setTwilioAccountSid] = useState('')
  const [twilioAuthToken, setTwilioAuthToken] = useState('')
  const [twilioStatus, setTwilioStatus] = useState<{
    configured: boolean
    accountSid?: string
    hasAuthToken?: boolean
    credentialsVerified?: boolean
    updatedAt?: string
  }>({ configured: false })
  const [twilioSaving, setTwilioSaving] = useState(false)
  const [twilioError, setTwilioError] = useState('')

  // Groq Cloud API key state
  const [groqApiKey, setGroqApiKey] = useState('')
  const [groqStatus, setGroqStatus] = useState<{
    configured: boolean
    maskedKey?: string
    verified?: boolean
    updatedAt?: string
    usingPlatformKey: boolean
  }>({ configured: false, usingPlatformKey: true })
  const [groqSaving, setGroqSaving] = useState(false)
  const [groqError, setGroqError] = useState('')

  // Agent voice state
  const [agentVoiceId, setAgentVoiceId] = useState<string | null>(null)
  const [voiceSaving, setVoiceSaving] = useState(false)

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
    loadTwilioStatus()
    loadGroqStatus()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await apiClient.getSettings()
      setSettings(data)
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const loadTwilioStatus = async () => {
    try {
      const status = await apiClient.getTwilioCredentialStatus()
      setTwilioStatus(status)
      if (status.accountSid) {
        setTwilioAccountSid(status.accountSid)
      }
    } catch (error) {
      console.error('Failed to load Twilio status:', error)
    }
  }

  const saveTwilioCredentials = async () => {
    if (!twilioAccountSid.trim() || !twilioAuthToken.trim()) {
      setTwilioError('Both Account SID and Auth Token are required')
      return
    }
    setTwilioSaving(true)
    setTwilioError('')
    try {
      await apiClient.saveTwilioCredentials({
        accountSid: twilioAccountSid.trim(),
        authToken: twilioAuthToken.trim(),
      })
      setTwilioAuthToken('')
      setMessage('Twilio credentials verified and saved!')
      setTimeout(() => setMessage(''), 3000)
      await loadTwilioStatus()
    } catch (error: any) {
      const msg = error?.response?.error || error?.message || 'Failed to save credentials'
      setTwilioError(msg)
    } finally {
      setTwilioSaving(false)
    }
  }

  const removeTwilioCredentials = async () => {
    try {
      await apiClient.deleteTwilioCredentials()
      setTwilioAccountSid('')
      setTwilioAuthToken('')
      setTwilioStatus({ configured: false })
      setMessage('Twilio credentials removed')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setTwilioError('Failed to remove credentials')
    }
  }

  // ── Groq Cloud handlers ─────────────────────────────────────────────────

  const loadGroqStatus = async () => {
    try {
      const status = await apiClient.getGroqKeyStatus()
      setGroqStatus(status)
    } catch (error) {
      console.error('Failed to load Groq status:', error)
    }
  }

  const saveGroqKey = async () => {
    if (!groqApiKey.trim()) {
      setGroqError('API key is required')
      return
    }
    if (!groqApiKey.startsWith('gsk_')) {
      setGroqError('Groq API keys start with gsk_')
      return
    }
    setGroqSaving(true)
    setGroqError('')
    try {
      await apiClient.saveGroqApiKey({ apiKey: groqApiKey.trim() })
      setGroqApiKey('')
      setMessage('Groq API key verified and saved!')
      setTimeout(() => setMessage(''), 3000)
      await loadGroqStatus()
    } catch (error: any) {
      const msg = error?.response?.error || error?.message || 'Failed to save Groq key'
      setGroqError(msg)
    } finally {
      setGroqSaving(false)
    }
  }

  const removeGroqKey = async () => {
    try {
      await apiClient.deleteGroqApiKey()
      setGroqApiKey('')
      setGroqStatus({ configured: false, usingPlatformKey: true })
      setMessage('Groq API key removed — using platform default')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setGroqError('Failed to remove key')
    }
  }

  const saveVoiceConfig = async (voiceId: string) => {
    setAgentVoiceId(voiceId)
    setVoiceSaving(true)
    try {
      await apiClient.configureVoice({ voice: voiceId, tone: '', language: '', personality: '' })
      setMessage('Agent voice updated!')
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      setMessage('Failed to update voice')
      setTimeout(() => setMessage(''), 3000)
    } finally {
      setVoiceSaving(false)
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
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="voice">Voice</TabsTrigger>
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

              <TabsContent value="voice" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Volume2 className="w-5 h-5" />
                      <span>Agent Voice</span>
                    </CardTitle>
                    <CardDescription>
                      Choose a preset voice or clone a custom one for your agents.
                      Powered by Chatterbox Turbo — self-hosted, zero cost per minute.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <VoiceSelector
                      value={agentVoiceId}
                      onChange={saveVoiceConfig}
                    />
                    {voiceSaving && (
                      <p className="text-sm text-muted-foreground mt-2">Saving…</p>
                    )}
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
                      <span>Twilio Credentials</span>
                    </CardTitle>
                    <CardDescription>
                      Connect your own Twilio account for phone number provisioning and voice calls.
                      Credentials are encrypted at rest with AES-256-GCM.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Status indicator */}
                    {twilioStatus.configured && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200 text-green-800">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          Twilio connected — Account {twilioStatus.accountSid}
                        </span>
                        {twilioStatus.updatedAt && (
                          <span className="text-xs text-green-600 ml-auto">
                            Updated {new Date(twilioStatus.updatedAt).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    )}

                    {twilioError && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm">{twilioError}</span>
                      </div>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="twilio-sid">Account SID</Label>
                      <Input
                        id="twilio-sid"
                        value={twilioAccountSid}
                        onChange={(e) => setTwilioAccountSid(e.target.value)}
                        placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                        autoComplete="off"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="twilio-token">Auth Token</Label>
                      <Input
                        id="twilio-token"
                        type="password"
                        value={twilioAuthToken}
                        onChange={(e) => setTwilioAuthToken(e.target.value)}
                        placeholder={twilioStatus.hasAuthToken ? '••••••••••••••••••••••••••••••••' : 'Enter your Auth Token'}
                        autoComplete="off"
                      />
                      <p className="text-xs text-muted-foreground">
                        {twilioStatus.hasAuthToken
                          ? 'Token is stored securely. Enter a new one to replace it.'
                          : 'Find your Auth Token in the Twilio Console.'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      <Button
                        onClick={saveTwilioCredentials}
                        disabled={twilioSaving}
                      >
                        {twilioSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        {twilioStatus.configured ? 'Update Credentials' : 'Verify & Save'}
                      </Button>

                      {twilioStatus.configured && (
                        <Button
                          variant="outline"
                          onClick={removeTwilioCredentials}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Disconnect
                        </Button>
                      )}

                      <a
                        href="https://console.twilio.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-auto text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
                      >
                        Open Twilio Console
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </CardContent>
                </Card>

                {/* Groq Cloud API Key */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Brain className="w-5 h-5" />
                      <span>Groq Cloud API Key</span>
                    </CardTitle>
                    <CardDescription>
                      Bring your own Groq Cloud API key for LLM inference and speech-to-text.
                      If not configured, the platform&apos;s shared key is used.
                      Credentials are encrypted at rest with AES-256-GCM.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Status indicator */}
                    {groqStatus.configured ? (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200 text-green-800">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          Your key: {groqStatus.maskedKey}
                        </span>
                        {groqStatus.updatedAt && (
                          <span className="text-xs text-green-600 ml-auto">
                            Updated {new Date(groqStatus.updatedAt).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-800">
                        <Zap className="w-4 h-4" />
                        <span className="text-sm">Using platform shared key — add your own for dedicated rate limits.</span>
                      </div>
                    )}

                    {groqError && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm">{groqError}</span>
                      </div>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="groq-key">API Key</Label>
                      <Input
                        id="groq-key"
                        type="password"
                        value={groqApiKey}
                        onChange={(e) => setGroqApiKey(e.target.value)}
                        placeholder={groqStatus.configured ? '••••••••••••••••••••••••••••••••' : 'gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
                        autoComplete="off"
                      />
                      <p className="text-xs text-muted-foreground">
                        {groqStatus.configured
                          ? 'Key is stored securely. Enter a new one to replace it.'
                          : 'Get your API key from the Groq Cloud console.'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      <Button
                        onClick={saveGroqKey}
                        disabled={groqSaving}
                      >
                        {groqSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        {groqStatus.configured ? 'Update Key' : 'Verify & Save'}
                      </Button>

                      {groqStatus.configured && (
                        <Button
                          variant="outline"
                          onClick={removeGroqKey}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Remove Key
                        </Button>
                      )}

                      <a
                        href="https://console.groq.com/keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-auto text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
                      >
                        Open Groq Console
                        <ExternalLink className="w-3 h-3" />
                      </a>
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