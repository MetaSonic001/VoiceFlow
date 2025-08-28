# FastAPI Backend Requirements for VoiceFlow AI Platform

## Overview
This document outlines the complete FastAPI backend requirements with CrewAI integration for the conversational AI platform.

## Environment Variables Required
\`\`\`bash
# Add this to your .env file
NEXT_PUBLIC_API_URL=http://localhost:8000
\`\`\`

## FastAPI Application Structure

### 1. Authentication Endpoints
\`\`\`python
# /auth/login - POST
# Request: { "email": str, "password": str }
# Response: { "token": str, "user": User }

# /auth/signup - POST  
# Request: { "email": str, "password": str, "company_name": str }
# Response: { "token": str, "user": User }

# /auth/me - GET
# Headers: Authorization: Bearer <token>
# Response: User object
\`\`\`

### 2. Onboarding Endpoints
\`\`\`python
# /onboarding/company - POST
# Request: CompanyProfile object
# Response: { "success": bool }

# /onboarding/agent - POST
# Request: AgentCreationData object  
# Response: { "agent_id": str }

# /onboarding/knowledge - POST
# Request: FormData with files and metadata
# Response: { "success": bool }
# Note: Process with CrewAI for document parsing and indexing

# /onboarding/voice - POST
# Request: VoicePersonalityData object
# Response: { "success": bool }

# /onboarding/channels - POST
# Request: ChannelSetupData object
# Response: { "success": bool }

# /onboarding/deploy - POST
# Request: { "agent_id": str }
# Response: { "success": bool, "phone_number": str }
\`\`\`

### 3. Agent Management Endpoints
\`\`\`python
# /agents - GET
# Response: List[Agent]

# /agents/{agent_id} - GET
# Response: AgentDetails object

# /agents/{agent_id} - PUT
# Request: Partial AgentUpdateData
# Response: { "success": bool }

# /agents/{agent_id} - DELETE
# Response: { "success": bool }

# /agents/{agent_id}/pause - POST
# Response: { "success": bool }

# /agents/{agent_id}/activate - POST
# Response: { "success": bool }

# /agents/pause-all - POST
# Response: { "success": bool }

# /agents/activate-all - POST
# Response: { "success": bool }
\`\`\`

### 4. Real-time & Conversation Endpoints
\`\`\`python
# /conversations/active - GET
# Response: List[LiveConversation]

# /conversations/{conversation_id}/transcript - GET
# Response: ConversationTranscript object

# /agents/{agent_id}/conversations - GET
# Query: limit (default: 10)
# Response: List[Conversation]

# WebSocket endpoint for real-time updates
# /ws - WebSocket connection
# Sends real-time metrics, conversation updates, agent status changes
\`\`\`

### 5. Analytics Endpoints
\`\`\`python
# /analytics/overview - GET
# Query: time_range (7d, 30d, 90d), agent_id (optional)
# Response: AnalyticsOverview object

# /analytics/metrics - GET
# Query: time_range, agent_id (optional)
# Response: MetricsData object

# /analytics/performance - GET
# Query: time_range, agent_id (optional)  
# Response: PerformanceData object

# /analytics/agents/comparison - GET
# Response: AgentComparisonData object

# /analytics/realtime - GET
# Response: RealtimeMetrics object
\`\`\`

### 6. Call Logs Endpoints
\`\`\`python
# /calls/logs - GET
# Query: page, limit, search, status, type, agent_id
# Response: CallLogsResponse object

# /calls/{call_id} - GET
# Response: CallLogDetails object
\`\`\`

## CrewAI Integration Points

### 1. Document Processing Agent
- **Purpose**: Process uploaded documents, FAQs, and knowledge base
- **Integration**: `/onboarding/knowledge` endpoint
- **Tasks**: Parse PDFs, extract text, create embeddings, index in vector DB

### 2. Conversation Agent
- **Purpose**: Handle real-time conversations using company knowledge
- **Integration**: WebSocket connections and conversation endpoints
- **Tasks**: Intent recognition, knowledge retrieval, response generation

### 3. Analytics Agent
- **Purpose**: Generate insights and analytics from conversation data
- **Integration**: Analytics endpoints
- **Tasks**: Performance analysis, trend detection, report generation

### 4. Voice Processing Agent
- **Purpose**: Handle speech-to-text and text-to-speech operations
- **Integration**: Real-time conversation handling
- **Tasks**: STT processing, TTS generation, voice personality application

## Database Schema Requirements

### Tables Needed:
1. **users** - User authentication and company info
2. **agents** - Agent configurations and metadata
3. **conversations** - Conversation logs and transcripts
4. **knowledge_base** - Processed documents and embeddings
5. **analytics** - Aggregated metrics and performance data
6. **channels** - Communication channel configurations

## WebSocket Implementation
- Real-time agent status updates
- Live conversation monitoring
- Performance metrics streaming
- Activity feed updates

## File Upload Handling
- Support for PDF, DOC, TXT files
- Website URL scraping
- Integration with vector databases
- CrewAI processing pipeline

## Security Requirements
- JWT token authentication
- Rate limiting on API endpoints
- File upload validation and scanning
- Data encryption for sensitive information

## Integration Files to Connect
The following frontend files are ready for API integration:

1. **components/auth-modal.tsx** - Connect to auth endpoints
2. **components/onboarding-flow.tsx** - Connect to onboarding endpoints  
3. **components/agent-dashboard.tsx** - Connect to agent management
4. **components/dashboard/live-conversations.tsx** - Connect to WebSocket
5. **components/analytics/** - Connect to analytics endpoints
6. **hooks/use-realtime-data.ts** - Connect to WebSocket for real-time data
7. **lib/api-client.ts** - All API methods are defined and ready

## Getting Started
1. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in your environment
2. Implement the FastAPI endpoints as specified above
3. Add CrewAI agents for document processing and conversation handling
4. Set up WebSocket for real-time features
5. The frontend will automatically connect to your backend

All frontend components are built with proper error handling, loading states, and will gracefully fall back to demo data if the API is unavailable.
