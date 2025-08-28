# FastAPI Integration Guide

This document outlines all the FastAPI endpoints needed to integrate with the VoiceFlow AI frontend platform.

## Base Configuration

- **Base URL**: `http://localhost:8000` (development)
- **Authentication**: Bearer token in Authorization header
- **Content-Type**: `application/json` (except file uploads)

## Authentication Endpoints

### POST /auth/signup
Create a new user account.

**Request Body:**
\`\`\`json
{
  "email": "user@company.com",
  "password": "securepassword",
  "company_name": "Acme Corporation"
}
\`\`\`

**Response:**
\`\`\`json
{
  "token": "jwt_token_here",
  "user": {
    "id": "user_id",
    "email": "user@company.com",
    "company_name": "Acme Corporation",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
\`\`\`

### POST /auth/login
Authenticate existing user.

**Request Body:**
\`\`\`json
{
  "email": "user@company.com",
  "password": "securepassword"
}
\`\`\`

**Response:** Same as signup

### GET /auth/me
Get current user information (requires authentication).

**Response:**
\`\`\`json
{
  "id": "user_id",
  "email": "user@company.com",
  "company_name": "Acme Corporation",
  "created_at": "2024-01-15T10:30:00Z"
}
\`\`\`

## Onboarding Endpoints

### POST /onboarding/company
Save company profile information.

**Request Body:**
\`\`\`json
{
  "company_name": "Acme Corporation",
  "industry": "technology",
  "use_case": "customer-support",
  "description": "Optional description"
}
\`\`\`

### POST /onboarding/agent
Create a new agent configuration.

**Request Body:**
\`\`\`json
{
  "name": "Customer Support Assistant",
  "role": "Customer Support Specialist",
  "description": "Handles customer inquiries",
  "channels": ["phone", "chat"]
}
\`\`\`

**Response:**
\`\`\`json
{
  "agent_id": "agent_12345"
}
\`\`\`

### POST /onboarding/knowledge
Upload knowledge base content (multipart/form-data).

**Form Data:**
- `files`: Multiple file uploads (PDF, DOC, TXT)
- `websites`: JSON array of website URLs
- `faq_text`: Plain text FAQ content

### POST /onboarding/voice
Configure voice and personality settings.

**Request Body:**
\`\`\`json
{
  "voice": "sarah",
  "tone": "professional",
  "personality": "Be helpful and patient...",
  "language": "en-US"
}
\`\`\`

### POST /onboarding/channels
Setup communication channels.

**Request Body:**
\`\`\`json
{
  "phone_number": "+1-555-123-4567",
  "chat_widget": {
    "enabled": true,
    "website_url": "https://company.com",
    "widget_color": "#6366f1"
  },
  "whatsapp": {
    "enabled": false
  },
  "email": {
    "enabled": false
  }
}
\`\`\`

### POST /onboarding/deploy
Deploy the agent and make it live.

**Request Body:**
\`\`\`json
{
  "agent_id": "agent_12345"
}
\`\`\`

**Response:**
\`\`\`json
{
  "success": true,
  "phone_number": "+1-555-123-4567"
}
\`\`\`

## Agent Management Endpoints

### GET /agents
Get all agents for the authenticated user.

**Response:**
\`\`\`json
[
  {
    "id": "agent_12345",
    "name": "Customer Support Assistant",
    "role": "Customer Support",
    "status": "active",
    "channels": ["phone", "chat"],
    "phone_number": "+1-555-123-4567",
    "total_calls": 1247,
    "total_chats": 892,
    "success_rate": 94,
    "avg_response_time": "2.3s",
    "last_active": "2 minutes ago",
    "created_at": "2024-01-15"
  }
]
\`\`\`

### GET /agents/{agent_id}
Get detailed information about a specific agent.

### PUT /agents/{agent_id}
Update agent configuration.

### DELETE /agents/{agent_id}
Delete an agent.

### POST /agents/{agent_id}/pause
Pause an active agent.

### POST /agents/{agent_id}/activate
Activate a paused agent.

### GET /agents/{agent_id}/conversations
Get recent conversations for an agent.

**Query Parameters:**
- `limit`: Number of conversations to return (default: 10)

## Analytics Endpoints

### GET /analytics/overview
Get overview metrics and KPIs.

**Query Parameters:**
- `time_range`: "24h", "7d", "30d", "90d" (default: "7d")
- `agent_id`: Filter by specific agent (optional)

**Response:**
\`\`\`json
{
  "total_interactions": 12847,
  "success_rate": 94.2,
  "avg_response_time": 2.1,
  "customer_satisfaction": 4.7,
  "interactions_change": "+15.2%",
  "success_rate_change": "+2.1%",
  "response_time_change": "-0.3s",
  "satisfaction_change": "+0.2"
}
\`\`\`

### GET /analytics/metrics
Get time-series data for charts.

**Response:**
\`\`\`json
{
  "data": [
    {
      "date": "2024-01-01",
      "calls": 120,
      "chats": 85,
      "total": 205
    }
  ]
}
\`\`\`

### GET /analytics/performance
Get performance trends over time.

### GET /analytics/agents/comparison
Get agent performance comparison data.

### GET /analytics/realtime
Get real-time activity metrics.

**Response:**
\`\`\`json
{
  "active_calls": 12,
  "active_chats": 8,
  "queued_interactions": 3,
  "online_agents": 3
}
\`\`\`

## Call Logs Endpoints

### GET /calls/logs
Get paginated call logs with filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `search`: Search query
- `status`: Filter by status ("completed", "escalated", "failed")
- `type`: Filter by type ("phone", "chat")
- `agent_id`: Filter by agent

**Response:**
\`\`\`json
{
  "logs": [
    {
      "id": "call_001",
      "type": "phone",
      "customer_info": "+1-555-987-6543",
      "agent_name": "Customer Support Assistant",
      "start_time": "2024-01-15T14:30:25Z",
      "duration": "3m 24s",
      "status": "completed",
      "resolution": "resolved",
      "summary": "Customer inquiry about pricing",
      "sentiment": "positive",
      "tags": ["pricing", "product-info"]
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "total_pages": 8
}
\`\`\`

### GET /calls/{call_id}
Get detailed call information including transcript.

**Response:**
\`\`\`json
{
  "id": "call_001",
  "type": "phone",
  "customer_info": "+1-555-987-6543",
  "agent_name": "Customer Support Assistant",
  "start_time": "2024-01-15T14:30:25Z",
  "duration": "3m 24s",
  "status": "completed",
  "resolution": "resolved",
  "summary": "Customer inquiry about pricing",
  "sentiment": "positive",
  "tags": ["pricing", "product-info"],
  "transcript": [
    {
      "speaker": "agent",
      "message": "Hello! How can I help you today?",
      "timestamp": "14:30:25"
    },
    {
      "speaker": "customer", 
      "message": "I'm interested in your pricing",
      "timestamp": "14:30:32"
    }
  ],
  "analysis": {
    "key_topics": ["pricing", "product-information"],
    "customer_intent": "pricing_inquiry",
    "resolution_quality": 0.95
  }
}
\`\`\`

## Error Handling

All endpoints should return appropriate HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (invalid/missing token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **422**: Unprocessable Entity (validation errors)
- **500**: Internal Server Error

Error responses should follow this format:
\`\`\`json
{
  "message": "Error description",
  "details": "Additional error details (optional)",
  "code": "ERROR_CODE"
}
\`\`\`

## CrewAI Integration Notes

Your FastAPI backend should integrate with CrewAI for:

1. **Agent Creation**: Use CrewAI to create and configure AI agents
2. **Knowledge Processing**: Process uploaded documents and create embeddings
3. **Conversation Handling**: Route conversations to appropriate CrewAI agents
4. **Analytics Generation**: Use CrewAI for conversation analysis and insights
5. **Voice Processing**: Integrate TTS/STT services with CrewAI workflows

## Environment Variables

The frontend expects these environment variables:

- `NEXT_PUBLIC_API_URL`: Your FastAPI base URL
- `NEXT_PUBLIC_WS_URL`: WebSocket URL for real-time features (optional)

## WebSocket Support (Optional)

For real-time features, consider implementing WebSocket endpoints:

- `/ws/realtime`: Real-time metrics updates
- `/ws/calls/{call_id}`: Live call monitoring
- `/ws/agents/{agent_id}`: Agent status updates
