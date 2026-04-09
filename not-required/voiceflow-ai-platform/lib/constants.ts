// API Configuration Constants
export const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000",
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
} as const

// Agent Status Constants
export const AGENT_STATUS = {
  ACTIVE: "active",
  PAUSED: "paused",
  DRAFT: "draft",
} as const

// Channel Types
export const CHANNEL_TYPES = {
  PHONE: "phone",
  CHAT: "chat",
  WHATSAPP: "whatsapp",
  EMAIL: "email",
} as const

// Call Status Constants
export const CALL_STATUS = {
  COMPLETED: "completed",
  ESCALATED: "escalated",
  FAILED: "failed",
  IN_PROGRESS: "in_progress",
} as const

// Sentiment Types
export const SENTIMENT_TYPES = {
  POSITIVE: "positive",
  NEGATIVE: "negative",
  NEUTRAL: "neutral",
} as const

// Time Range Options
export const TIME_RANGES = {
  "24h": "Last 24 hours",
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  "90d": "Last 90 days",
} as const

// Voice Options
export const VOICE_OPTIONS = [
  { id: "sarah", name: "Sarah", description: "Professional female voice, clear and friendly" },
  { id: "james", name: "James", description: "Professional male voice, warm and confident" },
  { id: "emma", name: "Emma", description: "Youthful female voice, energetic and approachable" },
  { id: "david", name: "David", description: "Mature male voice, authoritative and trustworthy" },
] as const

// Tone Options
export const TONE_OPTIONS = [
  { id: "professional", name: "Professional", description: "Formal, business-appropriate tone" },
  { id: "friendly", name: "Friendly", description: "Warm and approachable, casual but respectful" },
  { id: "empathetic", name: "Empathetic", description: "Understanding and supportive tone" },
  { id: "sales-driven", name: "Sales-Driven", description: "Persuasive and goal-oriented" },
] as const

// Industry Options
export const INDUSTRY_OPTIONS = [
  "Technology",
  "Healthcare",
  "Finance",
  "Retail",
  "Education",
  "Real Estate",
  "Consulting",
  "Other",
] as const

// Use Case Options
export const USE_CASE_OPTIONS = [
  { value: "customer-support", label: "Customer Support" },
  { value: "sales-lead-qualification", label: "Sales & Lead Qualification" },
  { value: "appointment-scheduling", label: "Appointment Scheduling" },
  { value: "hr-internal-helpdesk", label: "HR & Internal Helpdesk" },
  { value: "order-status-tracking", label: "Order Status & Tracking" },
  { value: "general-inquiries", label: "General Business Inquiries" },
] as const

// File Upload Limits
export const UPLOAD_LIMITS = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  MAX_FILES: 10,
  ALLOWED_TYPES: [".pdf", ".doc", ".docx", ".txt", ".md"],
} as const

// Pagination Defaults
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const
