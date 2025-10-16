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

  setClerkToken(token: string) {
    ;(globalThis as any).clerkToken = token
    localStorage.setItem("clerk_token", token)
  }

  private async getClerkToken(): Promise<string | null> {
    try {
      // Import Clerk dynamically to avoid SSR issues
      const { useAuth } = await import('@clerk/nextjs')
      // This is a workaround since we can't use hooks in class methods
      // We'll need to pass the token from components
      return null
    } catch (error) {
      console.warn('Clerk not available:', error)
      return null
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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

    // Add Clerk JWT token
    try {
      // For client-side, we'll need to get the token from Clerk
      // This will be set by components using the apiClient
      const token = (globalThis as any).clerkToken || localStorage.getItem("clerk_token")
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        }
      }
    } catch (error) {
      console.warn('Failed to get Clerk token:', error)
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
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
  // Auth helpers that persist token + user locally
  private persistAuth(token: string, user: any) {
    if (token) localStorage.setItem('auth_token', token)
    if (user) {
      localStorage.setItem('auth_user', JSON.stringify(user))
      // Set tenant ID for API requests
      if (user.tenantId) {
        this.setTenantId(user.tenantId)
      }
    }
  }

  async login(email: string, password: string) {
    const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    this.persistAuth(res.access_token, res.user)
    return res
  }

  async signup(email: string, password: string) {
    const res = await this.request<{ access_token: string; user: User }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    this.persistAuth(res.access_token, res.user)
    return res
  }

  async guestLogin() {
    const res = await this.request<{ access_token: string; user: User }>('/auth/guest', {
      method: 'POST',
    })
    this.persistAuth(res.access_token, res.user)
    return res
  }

  async logout() {
    // remove local persisted token and call server for symmetry
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    try {
      await this.request<{ success: boolean }>('/auth/logout', { method: 'POST' })
    } catch (err) {
      // ignore network errors on logout
    }
    return { success: true }
  }

  async getCurrentUser() {
    // prefer token-derived user from localStorage
    const raw = localStorage.getItem('auth_user')
    if (raw) return JSON.parse(raw)
    const res = await this.request<{ user: User }>('/auth/me')
    return res.user
  }

  // Onboarding endpoints
  async saveCompanyProfile(data: CompanyProfile) {
    return this.request<{ success: boolean }>("/onboarding/company", {
      method: "POST",
      body: JSON.stringify(data),
    })
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

  // Real-time WebSocket connection
  connectWebSocket(onMessage: (data: any) => void) {
    const wsUrl = this.baseUrl.replace("http", "ws") + "/ws"
    console.log("[v0] Connecting to WebSocket:", wsUrl)

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log("[v0] WebSocket connected")
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage(data)
        } catch (error) {
          console.error("[v0] Failed to parse WebSocket message:", error)
        }
      }

      ws.onerror = (error) => {
        console.error("[v0] WebSocket error:", error)
      }

      ws.onclose = () => {
        console.log("[v0] WebSocket disconnected")
      }

      return ws
    } catch (error) {
      console.error("[v0] Failed to create WebSocket connection:", error)
      return null
    }
  }

  // Real-time conversation monitoring endpoints
  async getActiveConversations() {
    return this.request<LiveConversation[]>("/conversations/active")
  }

  async getConversationTranscript(conversationId: string) {
    return this.request<ConversationTranscript>(`/conversations/${conversationId}/transcript`)
  }

  async pauseAllAgents() {
    return this.request<{ success: boolean }>("/agents/pause-all", {
      method: "POST",
    })
  }

  async activateAllAgents() {
    return this.request<{ success: boolean }>("/agents/activate-all", {
      method: "POST",
    })
  }

  // Analytics endpoints
  async getAnalyticsOverview(timeRange = "7d", agentId?: string) {
    const params = new URLSearchParams({ time_range: timeRange })
    if (agentId && agentId !== "all") {
      params.append("agent_id", agentId)
    }
    return this.request<AnalyticsOverview>(`/analytics/overview?${params}`)
  }

  async getMetricsData(timeRange = "7d", agentId?: string) {
    const params = new URLSearchParams({ time_range: timeRange })
    if (agentId && agentId !== "all") {
      params.append("agent_id", agentId)
    }
    return this.request<MetricsData>(`/analytics/metrics?${params}`)
  }

  async getPerformanceData(timeRange = "7d", agentId?: string) {
    const params = new URLSearchParams({ time_range: timeRange })
    if (agentId && agentId !== "all") {
      params.append("agent_id", agentId)
    }
    return this.request<PerformanceData>(`/analytics/performance?${params}`)
  }

  async getMetricsChart(timeRange = "7d", agentId?: string) {
    const params = new URLSearchParams({ time_range: timeRange })
    if (agentId && agentId !== "all") {
      params.append("agent_id", agentId)
    }
    return this.request<MetricsChartData>(`/analytics/metrics-chart?${params}`)
  }

  async getAgentComparison() {
    return this.request<AgentComparisonData>("/analytics/agents/comparison")
  }

  async getRealtimeMetrics() {
    return this.request<RealtimeMetrics>("/analytics/realtime")
  }

  // Call logs endpoints
  async getCallLogs(params: CallLogsParams = {}) {
    const searchParams = new URLSearchParams()

    if (params.page) searchParams.append("page", params.page.toString())
    if (params.limit) searchParams.append("limit", params.limit.toString())
    if (params.search) searchParams.append("search", params.search)
    if (params.status) searchParams.append("status", params.status)
    if (params.type) searchParams.append("type", params.type)
    if (params.agent_id) searchParams.append("agent_id", params.agent_id)

    return this.request<CallLogsResponse>(`/analytics/calls?${searchParams}`)
  }

  async getCallDetails(callId: string) {
    return this.request<CallLogDetails>(`/calls/${callId}`)
  }

  async getConversations(agentId: string, limit = 10) {
    return this.request<Conversation[]>(`/agents/${agentId}/conversations?limit=${limit}`)
  }

  async sendMessage(sessionId: string, message: string) {
    return this.request<{ response: string; chunks_used?: string[] }>(`/conversations/${sessionId}/message`, {
      method: "POST",
      body: JSON.stringify({ message }),
    })
  }

  async sendAudioMessage(sessionId: string, audioFile: File) {
    const formData = new FormData()
    formData.append("audio", audioFile)

    return this.request<{ response: string; transcript?: string }>(`/conversations/${sessionId}/audio`, {
      method: "POST",
      body: formData,
      headers: {}, // Remove Content-Type for FormData
    })
  }

  async healthCheck() {
    return this.request<{ status: string; timestamp: string }>("/health")
  }

  // Generic helper for POSTing raw payloads from components
  async postRaw<T = any>(endpoint: string, body: any, headers: Record<string, string> = {}) {
    const options: RequestInit = {
      method: 'POST',
      body: typeof body === 'string' ? body : JSON.stringify(body),
      headers: { 'Content-Type': 'application/json', ...headers },
    }
    return this.request<T>(endpoint, options)
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

export interface AgentCreationData {
  name: string
}

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
