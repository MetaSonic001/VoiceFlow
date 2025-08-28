// API Client Configuration and Utilities
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

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

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
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

    // Add auth token if available
    const token = localStorage.getItem("auth_token")
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      }
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

  // Auth endpoints
  async login(email: string, password: string) {
    return this.request<{ token: string; user: User; session_id: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })
  }

  async signup(email: string, password: string, companyName: string) {
    return this.request<{ token: string; user: User; session_id: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, company_name: companyName }),
    })
  }

  async getCurrentUser() {
    return this.request<User>("/auth/me")
  }

  async logout() {
    return this.request<{ success: boolean }>("/auth/logout", {
      method: "POST",
    })
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

  async deployAgent(agentId: string) {
    return this.request<{ success: boolean; phone_number?: string }>("/onboarding/deploy", {
      method: "POST",
      body: JSON.stringify({ agent_id: agentId }),
    })
  }

  async getDeploymentStatus(agentId: string) {
    return this.request<{ status: string; message: string }>(`/onboarding/status?agent_id=${agentId}`)
  }

  // Agent management endpoints
  async getAgents() {
    return this.request<Agent[]>("/agents")
  }

  async getAgent(agentId: string) {
    return this.request<AgentDetails>(`/agents/${agentId}`)
  }

  async updateAgent(agentId: string, data: Partial<AgentUpdateData>) {
    return this.request<{ success: boolean }>(`/agents/${agentId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteAgent(agentId: string) {
    return this.request<{ success: boolean }>(`/agents/${agentId}`, {
      method: "DELETE",
    })
  }

  async pauseAgent(agentId: string) {
    return this.request<{ success: boolean }>(`/agents/${agentId}/pause`, {
      method: "POST",
    })
  }

  async activateAgent(agentId: string) {
    return this.request<{ success: boolean }>(`/agents/${agentId}/activate`, {
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

    return this.request<CallLogsResponse>(`/calls/logs?${searchParams}`)
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
  personality?: string
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
