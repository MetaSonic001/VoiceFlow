// API Client Configuration and Utilities
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
// Runner requests are proxied through the backend orchestrator
const AGENT_RUNNER_URL = undefined

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: any,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

class ApiClient {
  private baseUrl: string
  private tenantId: string | null = null
  private tokenProvider: (() => Promise<string | null>) | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
    // Try to get tenant ID from localStorage on initialization
    if (typeof window !== 'undefined') {
      const user = localStorage.getItem('auth_user')
      if (user) {
        try {
          const userData = JSON.parse(user)
          this.tenantId = userData.tenantId
        } catch (e) {
          console.warn('Failed to parse user data for tenant ID')
        }
      }
    }
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId
  }

  // Called once from AutoAuth to wire up fresh-token retrieval on every request
  setTokenProvider(provider: () => Promise<string | null>) {
    this.tokenProvider = provider
  }

  private async request<T>(endpoint: string, options: RequestInit = {}, _isRetry = false): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const config: RequestInit = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    }

    // Add tenant ID header for multi-tenant isolation
    if (this.tenantId) {
      config.headers = {
        ...config.headers,
        'x-tenant-id': this.tenantId,
      }
    }

    // Get a fresh auth token for every request
    try {
      const token = this.tokenProvider ? await this.tokenProvider() : null
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        }
      }
    } catch (error) {
      console.warn('Failed to get auth token:', error)
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        // On 401, retry once with a fresh token (handles edge case of token expiring mid-flight)
        if (response.status === 401 && !_isRetry && this.tokenProvider) {
          return this.request<T>(endpoint, options, true)
        }
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(errorData.message || `HTTP ${response.status}`, response.status, errorData)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError("Network error", 0, error)
    }
  }

  // Helper to extract a friendly message from an error
  safeParseError(err: any) {
    if (!err) return 'Unknown error'
    if (err instanceof ApiError) return err.response?.message || err.message || `HTTP ${err.status}`
    if (err?.message) return err.message
    return String(err)
  }

  // Auth endpoints
  private persistAuth(_token: string, user: any) {
    if (typeof window === 'undefined') return
    if (user) {
      localStorage.setItem('auth_user', JSON.stringify(user))
      if (user.tenantId) {
        this.setTenantId(user.tenantId)
      }
    }
  }

  async getCurrentUser() {
    const raw = typeof window !== 'undefined' ? localStorage.getItem('auth_user') : null
    if (raw) return JSON.parse(raw)
    return null
  }

  // Onboarding endpoints
  async saveCompanyProfile(data: {
    company_name: string
    industry: string
    use_case: string
    website_url?: string
    description?: string
  }) {
    return this.request<{ success: boolean; scrapeJobId?: string }>("/onboarding/company", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getCompanyProfile() {
    return this.request<{
      company_name: string | null
      industry: string | null
      use_case: string | null
      website_url: string | null
      description: string | null
    }>("/onboarding/company")
  }

  // LinkedIn-style company search against the seed list
  async searchCompanies(q: string) {
    return this.request<{
      companies: Array<{
        id: string
        name: string
        domain: string
        industry: string
        description?: string
      }>
    }>(`/onboarding/company-search?q=${encodeURIComponent(q)}`)
  }

  // Poll the status of a background company scraping job
  async getCompanyScrapingStatus(jobId: string) {
    return this.request<{
      status: string
      progress: string
      chunks_processed: number
      pages_scraped: number
    }>(`/onboarding/scrape-status/${jobId}`)
  }

  // Fetch company knowledge chunks from ChromaDB (for the knowledge dashboard)
  async getCompanyKnowledge() {
    return this.request<{
      chunks: Array<{ id: string; content: string; metadata: any }>
      total: number
    }>(`/onboarding/company-knowledge`)
  }

  // Delete a single chunk from the company knowledge base
  async deleteCompanyKnowledge(chunkId: string) {
    return this.request<{ deleted: boolean }>(
      `/onboarding/company-knowledge/${encodeURIComponent(chunkId)}`,
      { method: "DELETE" }
    )
  }

  async triggerUrlIngestion(url: string, agentId?: string) {
    return this.request<{ jobId: string; status: string }>('/api/ingestion/start', {
      method: 'POST',
      body: JSON.stringify({ urls: [url], agentId: agentId ?? 'knowledge_base' }),
    });
  }

  async getIngestionStatus(jobId: string) {
    return this.request<{ status: string; progress?: number | string; chunks_processed?: number; pages_scraped?: number }>(
      `/api/ingestion/status/${jobId}`
    );
  }

  // ── Call / Conversation Logs ─────────────────────────────────────────────

  async getCallLogs(params?: {
    agentId?: string
    from?: string   // ISO date string
    to?: string     // ISO date string
    page?: number
    limit?: number
  }) {
    const qs = new URLSearchParams()
    if (params?.agentId) qs.set('agentId', params.agentId)
    if (params?.from)    qs.set('from', params.from)
    if (params?.to)      qs.set('to', params.to)
    if (params?.page)    qs.set('page', String(params.page))
    if (params?.limit)   qs.set('limit', String(params.limit))
    const query = qs.toString() ? `?${qs.toString()}` : ''
    return this.request<{
      logs: Array<{
        id: string
        tenantId: string
        agentId: string
        startedAt: string
        endedAt: string | null
        durationSeconds: number | null
        transcript: string
        rating: number | null
        ratingNotes: string | null
        flaggedForRetraining: boolean
        createdAt: string
        agent: { id: string; name: string }
      }>
      total: number
      page: number
      limit: number
      pages: number
    }>(`/api/logs${query}`)
  }

  async rateCallLog(id: string, rating: 1 | -1, notes?: string) {
    return this.request<{ id: string; rating: number }>(`/api/logs/${id}/rating`, {
      method: 'PATCH',
      body: JSON.stringify({ rating, notes }),
    })
  }

  async flagCallLogForRetraining(id: string) {
    return this.request<{ id: string; flaggedForRetraining: boolean }>(`/api/logs/${id}/flag`, {
      method: 'POST',
    })
  }

  // ── Retraining Pipeline ─────────────────────────────────────────────────

  async getRetrainingExamples(params?: { page?: number; limit?: number; status?: string; agentId?: string }) {
    const qs = new URLSearchParams()
    if (params?.page) qs.append('page', String(params.page))
    if (params?.limit) qs.append('limit', String(params.limit))
    if (params?.status) qs.append('status', params.status)
    if (params?.agentId) qs.append('agentId', params.agentId)
    return this.request<{
      examples: Array<{
        id: string; tenantId: string; agentId: string; callLogId: string;
        userQuery: string; badResponse: string; idealResponse: string;
        status: string; approvedAt: string | null; createdAt: string;
        agent: { id: string; name: string };
        callLog: { id: string; startedAt: string; rating: number | null };
      }>;
      total: number; page: number; limit: number; pages: number;
    }>(`/api/retraining?${qs.toString()}`)
  }

  async getRetrainingStats() {
    return this.request<{
      pending: number; approved: number; rejected: number; flaggedNotProcessed: number;
    }>('/api/retraining/stats')
  }

  async updateRetrainingExample(id: string, data: { idealResponse?: string; status?: 'pending' | 'approved' | 'rejected' }) {
    return this.request(`/api/retraining/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteRetrainingExample(id: string) {
    return this.request<{ deleted: boolean }>(`/api/retraining/${id}`, { method: 'DELETE' })
  }

  async triggerRetrainingPipeline() {
    return this.request<{ processed: boolean; examplesCreated: number }>('/api/retraining/process', {
      method: 'POST',
    })
  }

  // ── Agent Templates ───────────────────────────────────────────────────────

  async getAgentTemplates() {
    return this.request<{
      templates: Array<{
        id: string
        name: string
        description: string
        defaultCapabilities: string[]
        suggestedKnowledgeCategories: string[]
        defaultTools: string[]
        icon: string | null
      }>
    }>('/api/templates')
  }

  async getAgentTemplate(id: string) {
    return this.request<{
      id: string
      name: string
      description: string
      baseSystemPrompt: string
      defaultCapabilities: string[]
      suggestedKnowledgeCategories: string[]
      defaultTools: string[]
      icon: string | null
    }>(`/api/templates/${id}`)
  }

  async createAgent(data: AgentCreationData) {
    return this.request<{ agent_id: string }>("/onboarding/agent", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async uploadKnowledge(data: KnowledgeUploadData) {
    const formData = new FormData()

    // Add files
    data.files?.forEach((file, index) => {
      formData.append(`files`, file)
    })

    // Add other data
    formData.append("websites", JSON.stringify(data.websites || []))
    formData.append("faq_text", data.faqText || "")

    return this.request<{ success: boolean }>("/onboarding/knowledge", {
      method: "POST",
      body: formData,
      headers: {}, // Remove Content-Type to let browser set it for FormData
    })
  }

  async configureVoice(data: VoicePersonalityData) {
    return this.request<{ success: boolean }>("/onboarding/voice", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async setupChannels(data: ChannelSetupData) {
    return this.request<{ success: boolean }>("/onboarding/channels", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async saveAgentConfiguration(data: AgentConfigurationData) {
    return this.request<{
      success: boolean;
      message: string;
      agent_id: string;
      chroma_collection: string;
    }>("/onboarding/agent-config", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  // Fetch Twilio incoming phone numbers from backend
  async getTwilioNumbers() {
    return this.request<{ numbers: Array<{ sid?: string; phone_number?: string; friendly_name?: string }> }>("/twilio/numbers")
  }

  async deployAgent(agentId: string) {
    return this.request<{ success: boolean; phone_number?: string }>("/onboarding/deploy", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId }),
    })
  }

  async getDeploymentStatus(agentId: string) {
    return this.request<{ status: string; message: string }>(`/onboarding/status?agent_id=${agentId}`)
  }

  // Onboarding progress persistence (server-side resume)
  async saveOnboardingProgress(payload: { agent_id?: number | string; current_step?: number; data?: any }) {
    return this.request<{ success: boolean; progress_id?: number; agent_id?: number; current_step?: number; data?: any }>(`/onboarding/progress`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: payload.agent_id, current_step: payload.current_step, data: payload.data }),
    })
  }

  async getOnboardingProgress() {
    return this.request<{ exists: boolean; progress_id?: number; agent_id?: number; current_step?: number; data?: any }>(`/onboarding/progress`)
  }

  async deleteOnboardingProgress() {
    return this.request<{ deleted: boolean }>(`/onboarding/progress`, { method: 'DELETE' })
  }

  // Agent management endpoints
  async getAgents(params: { page?: number; limit?: number; search?: string; status?: string } = {}) {
    const qs = new URLSearchParams()
    if (params.page) qs.append('page', String(params.page))
    if (params.limit) qs.append('limit', String(params.limit))
    if (params.search) qs.append('search', params.search)
    if (params.status) qs.append('status', params.status)
    // Call Next.js server route under /api which will proxy to Prisma/backend as needed
    return this.request<{ agents: Agent[]; total: number; page: number; limit: number }>(`/api/agents?${qs.toString()}`)
  }

  // Pipeline admin
  async createPipelineAgent(data: { tenant_id: string; name: string; agent_type: string; agent_id?: string; config?: any }) {
    return this.request<{ id: string; name: string }>("/admin/pipeline_agents", {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listPipelineAgents() {
    return this.request<{ pipeline_agents: any[] }>("/admin/pipeline_agents")
  }

  async createPipeline(data: { tenant_id: string; name: string; agent_id?: string; stages: any[] }) {
    return this.request<{ id: string; name: string }>("/admin/pipelines", {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listPipelines() {
    return this.request<{ pipelines: any[] }>("/admin/pipelines")
  }

  async triggerPipeline(pipelineId: string, targetAgentId?: string) {
    const body = { pipeline_id: pipelineId, target_agent_id: targetAgentId }
    return this.request<{ status: string }>(`/admin/pipelines/trigger`, {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  // Agent-runner operations are proxied through backend endpoints under /runner/*
  async runnerCreateAgent(data: { name: string; agent_type: string; config?: any }) {
    return this.request<{ id: number; name: string }>(`/runner/agents`, { method: 'POST', body: JSON.stringify(data) })
  }

  async runnerListAgents() {
    return this.request<any[]>(`/runner/agents`)
  }

  async runnerCreatePipeline(data: { name: string; tenant_id?: string; stages: any[] }) {
    return this.request<{ id: number; name: string }>(`/runner/pipelines`, { method: 'POST', body: JSON.stringify(data) })
  }

  async runnerListPipelines() {
    return this.request<any[]>(`/runner/pipelines`)
  }

  async runnerTriggerPipeline(pipelineId: number) {
    return this.request<{ message: string }>(`/runner/pipelines/${pipelineId}/trigger`, { method: 'POST', body: JSON.stringify({}) })
  }

  async runnerTriggerPipelineWithContext(pipelineId: number, context: any) {
    return this.request<{ message: string }>(`/runner/pipelines/${pipelineId}/trigger`, { method: 'POST', body: JSON.stringify(context) })
  }

  async getAgent(agentId: string) {
    return this.request<AgentDetails>(`/api/agents/${agentId}`)
  }

  async updateAgent(agentId: string, data: Partial<AgentUpdateData>) {
    return this.request<{ success: boolean }>(`/api/agents/${agentId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteAgent(agentId: string) {
    return this.request<{ success: boolean }>(`/api/agents/${agentId}`, {
      method: "DELETE",
    })
  }

  async pauseAgent(agentId: string) {
    return this.request<{ success: boolean }>(`/api/agents/${agentId}/pause`, {
      method: "POST",
    })
  }

  async activateAgent(agentId: string) {
    return this.request<{ success: boolean }>(`/api/agents/${agentId}/activate`, {
      method: "POST",
    })
  }

  // User management methods
  async getUsers(params: { page?: number; limit?: number; search?: string; role?: string; status?: string } = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });
    return this.request<User[]>('/api/users?' + queryParams.toString());
  }

  async getUser(userId: string) {
    return this.request<User>(`/api/users/${userId}`);
  }

  async createUser(data: { email: string; name: string; role?: string; status?: string }) {
    return this.request<User>('/api/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateUser(userId: string, data: Partial<{ email: string; name: string; role: string; status: string }>) {
    return this.request<User>(`/api/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteUser(userId: string) {
    return this.request<{ success: boolean }>(`/api/users/${userId}`, {
      method: 'DELETE',
    });
  }

  // Analytics methods
  async getAnalyticsOverview(params: { timeRange?: string; agentId?: string } | string = {}, agentIdCompat?: string) {
    // Support both object-style and positional args for backward compat
    let queryObj: Record<string, string> = {};
    if (typeof params === 'string') {
      queryObj.timeRange = params;
      if (agentIdCompat && agentIdCompat !== 'all') queryObj.agentId = agentIdCompat;
    } else {
      if (params.timeRange) queryObj.timeRange = params.timeRange;
      if (params.agentId && params.agentId !== 'all') queryObj.agentId = params.agentId;
    }
    const queryParams = new URLSearchParams(queryObj);
    return this.request('/analytics/overview?' + queryParams.toString());
  }

  async getRealtimeMetrics() {
    return this.request('/analytics/realtime');
  }

  async getMetricsChart(timeRange?: string, agentId?: string) {
    const queryParams = new URLSearchParams();
    if (timeRange) queryParams.append('timeRange', timeRange);
    if (agentId && agentId !== 'all') queryParams.append('agentId', agentId);
    return this.request('/analytics/metrics-chart?' + queryParams.toString());
  }

  async getPerformanceData(timeRange?: string, agentId?: string) {
    // Performance data derived from metrics-chart — uses the same endpoint
    const queryParams = new URLSearchParams();
    if (timeRange) queryParams.append('timeRange', timeRange);
    if (agentId && agentId !== 'all') queryParams.append('agentId', agentId);
    return this.request('/analytics/metrics-chart?' + queryParams.toString());
  }

  async getAgentComparison(timeRange?: string) {
    const queryParams = new URLSearchParams();
    if (timeRange) queryParams.append('timeRange', timeRange);
    return this.request('/analytics/agent-comparison?' + queryParams.toString());
  }

  async getChatLogs(params: { page?: number; limit?: number; search?: string; status?: string; agentId?: string } = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });
    return this.request('/analytics/calls?' + queryParams.toString());
  }

  // Knowledge base methods
  async getKnowledgeBase(params: { page?: number; limit?: number; search?: string } = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });
    return this.request('/api/documents?' + queryParams.toString());
  }

  async uploadDocument(data: FormData) {
    return this.request('/api/documents', {
      method: 'POST',
      body: data,
      headers: {
        // Don't set Content-Type for FormData - let browser set it with boundary
      },
    });
  }

  async deleteDocument(documentId: string) {
    return this.request<{ success: boolean }>(`/api/documents/${documentId}`, {
      method: 'DELETE',
    });
  }

  // Settings methods
  async getSettings() {
    return this.request('/settings');
  }

  async updateSettings(data: any) {
    return this.request('/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ── Twilio Credentials (per-tenant) ─────────────────────────────────────

  async saveTwilioCredentials(data: { accountSid: string; authToken: string }) {
    return this.request<{ success: boolean; message: string; accountSid: string }>(
      '/api/settings/twilio',
      { method: 'POST', body: JSON.stringify(data) },
    )
  }

  async getTwilioCredentialStatus() {
    return this.request<{
      configured: boolean
      accountSid?: string
      hasAuthToken?: boolean
      credentialsVerified?: boolean
      updatedAt?: string
    }>('/api/settings/twilio')
  }

  async deleteTwilioCredentials() {
    return this.request<{ success: boolean }>('/api/settings/twilio', { method: 'DELETE' })
  }

  // ── Groq Cloud API Key (per-tenant) ─────────────────────────────────────

  async saveGroqApiKey(data: { apiKey: string }) {
    return this.request<{ success: boolean; message: string; maskedKey: string }>(
      '/api/settings/groq',
      { method: 'POST', body: JSON.stringify(data) },
    )
  }

  async getGroqKeyStatus() {
    return this.request<{
      configured: boolean
      maskedKey?: string
      verified?: boolean
      updatedAt?: string
      usingPlatformKey: boolean
    }>('/api/settings/groq')
  }

  async deleteGroqApiKey() {
    return this.request<{ success: boolean }>('/api/settings/groq', { method: 'DELETE' })
  }

  async getGroqModels() {
    return this.request<{
      models: Array<{
        id: string
        name: string
        speed: string
        contextWindow: number
        maxCompletionTokens: number
        description: string
      }>
    }>('/api/settings/groq/models')
  }

  // ── TTS / Voice ─────────────────────────────────────────────────────────

  async getPresetVoices() {
    return this.request<{
      voices: Array<{ id: string; name: string; description: string; sampleUrl: string | null }>
    }>('/api/tts/preset-voices')
  }

  async synthesisePreview(text: string, voiceId: string) {
    return this.request<{ audioUrl: string; cached: boolean }>('/api/tts/synthesise', {
      method: 'POST',
      body: JSON.stringify({ text, voiceId }),
    })
  }

  async cloneVoice(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request<{ voiceId: string; testAudioUrl: string }>('/api/tts/clone-voice', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    })
  }

  // System methods
  async getSystemHealth() {
    return this.request('/health');
  }

  async getSystemLogs(params: { level?: string; limit?: number; from?: string; to?: string } = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });
    return this.request('/system/logs?' + queryParams.toString());
  }

  async getSystemMetrics() {
    return this.request('/system/metrics');
  }

  // Notifications methods
  async getNotifications(params: { page?: number; limit?: number; read?: boolean } = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });
    return this.request('/notifications?' + queryParams.toString());
  }

  async markNotificationAsRead(notificationId: string) {
    return this.request('/notifications/' + notificationId + '/read', {
      method: 'POST',
    });
  }

  async markAllNotificationsAsRead() {
    return this.request('/notifications/mark-all-read', {
      method: 'POST',
    });
  }

  // Backup methods
  async createBackup(data: { type: 'full' | 'incremental'; description?: string }) {
    return this.request<{ backupId: string; status: string }>('/backup/create', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getBackups(params: { page?: number; limit?: number; status?: string } = {}) {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString());
    });
    return this.request('/backup?' + queryParams.toString());
  }

  async restoreBackup(backupId: string) {
    return this.request('/backup/' + backupId + '/restore', {
      method: 'POST',
    });
  }

  // Billing / Usage methods
  async getUsageStats(params: { timeRange?: string } = {}) {
    return this.request<{ agents: number; callLogs: number; documents: number }>('/analytics/usage');
  }

  // Integrations methods
  async getIntegrations() {
    return this.request('/integrations');
  }

  async connectIntegration(data: { type: string; config: any }) {
    return this.request('/integrations/connect', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async disconnectIntegration(integrationId: string) {
    return this.request('/integrations/' + integrationId + '/disconnect', {
      method: 'POST',
    });
  }

  async testIntegration(integrationId: string) {
    return this.request('/integrations/' + integrationId + '/test', {
      method: 'POST',
    });
  }
}

export const apiClient = new ApiClient()

// Types for API responses and requests
export interface User {
  id: string
  email: string
  company_name: string
  created_at: string
}

export interface CompanyProfile {
  company_name: string
  industry: string
  use_case: string
  description?: string
}

export interface AgentCreationData {
  name: string
  role: string
  templateId?: string
  description?: string
  channels: string[]
}

export interface KnowledgeUploadData {
  files?: File[]
  websites?: string[]
  faqText?: string
}

export interface VoicePersonalityData {
  voice: string
  tone: string
  personality: string[]
  language: string
}

export interface ChannelSetupData {
  phone_number?: string
  chat_widget: {
    enabled: boolean
    website_url?: string
    widget_color?: string
  }
  whatsapp?: {
    enabled: boolean
    business_number?: string
  }
  email?: {
    enabled: boolean
    forwarding_address?: string
  }
}

export interface Agent {
  id: string
  name: string
  role: string
  status: "active" | "paused" | "draft"
  channels: string[]
  phone_number?: string
  total_calls: number
  total_chats: number
  success_rate: number
  avg_response_time: string
  last_active: string
  created_at: string
}

export interface AgentDetails extends Agent {
  description?: string
  voice_config: VoicePersonalityData
  channel_config: ChannelSetupData
  knowledge_base: {
    documents: number
    websites: number
    faq_entries: number
  }
}

export interface AgentUpdateData {
  name?: string
  role?: string
  description?: string
  voice_config?: VoicePersonalityData
  channel_config?: ChannelSetupData
  llmPreferences?: { model?: string }
  tokenLimit?: number
  contextWindowStrategy?: string
}

export interface AnalyticsOverview {
  total_interactions: number
  success_rate: number
  avg_response_time: number
  customer_satisfaction: number
  interactions_change: string
  success_rate_change: string
  response_time_change: string
  satisfaction_change: string
}

export interface MetricsData {
  data: Array<{
    date: string
    calls: number
    chats: number
    total: number
  }>
}

export interface PerformanceData {
  data: Array<{
    date: string
    success_rate: number
    response_time: number
    satisfaction: number
  }>
}

export interface AgentComparisonData {
  agents: Array<{
    id: string
    name: string
    interactions: number
    success_rate: number
    avg_response_time: number
    status: string
  }>
}

export interface MetricsChartData {
  labels: string[]
  datasets: Array<{
    label: string
    data: number[]
    borderColor: string
    backgroundColor: string
  }>
}

export interface RealtimeMetrics {
  active_calls: number
  active_chats: number
  queued_interactions: number
  online_agents: number
}

export interface CallLogsParams {
  page?: number
  limit?: number
  search?: string
  status?: string
  type?: string
  agent_id?: string
}

export interface CallLogsResponse {
  logs: CallLog[]
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface CallLog {
  id: string
  type: "phone" | "chat"
  customer_info: string
  agent_name: string
  start_time: string
  duration: string
  status: "completed" | "escalated" | "failed"
  resolution: string
  summary: string
  sentiment: "positive" | "negative" | "neutral"
  tags: string[]
}

export interface CallLogDetails extends CallLog {
  transcript: Array<{
    speaker: "agent" | "customer"
    message: string
    timestamp: string
  }>
  analysis: {
    key_topics: string[]
    customer_intent: string
    resolution_quality: number
  }
}

export interface Conversation {
  id: string
  type: "phone" | "chat"
  customer_info: string
  duration: string
  status: string
  timestamp: string
  summary: string
}

// New types for real-time features
export interface LiveConversation {
  id: string
  type: "phone" | "chat"
  agentName: string
  customerInfo: string
  duration: string
  status: "active" | "on_hold" | "transferring"
  lastMessage: string
  sentiment: "positive" | "neutral" | "negative"
}

export interface ConversationTranscript {
  conversationId: string
  messages: Array<{
    speaker: "agent" | "customer"
    message: string
    timestamp: string
  }>
}

export interface HealthCheckResponse {
  status: string
  timestamp: string
}

// Onboarding types
export interface CompanyProfile {
  name: string
  industry: string
  useCase: string
  description?: string
}

// AgentCreationData defined above (near line 724) — not duplicated here

export interface KnowledgeUploadData {
  files?: File[]
  websites?: string[]
  faqText?: string
}

export interface VoicePersonalityData {
  voice: string
  personality: string[]
}

export interface ChannelSetupData {
  channels: string[]
  phone_number?: string
}

export interface AgentConfigurationData {
  agent_name?: string
  agent_role?: string
  agent_description?: string
  personality_traits?: string[]
  communication_channels?: string[]
  preferred_response_style?: string
  response_tone?: string
  company_name?: string
  industry?: string
  primary_use_case?: string
  brief_description?: string
  behavior_rules?: any
  escalation_triggers?: any
  knowledge_boundaries?: any
  max_response_length?: number
  confidence_threshold?: number
}
