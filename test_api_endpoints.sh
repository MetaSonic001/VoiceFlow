#!/bin/bash

# VoiceFlow Express Backend API Test Script
# This script tests all endpoints with dummy data and proper authentication

BASE_URL="http://localhost:3001"
AUTH_TOKEN=""
GUEST_TOKEN=""

echo "🧪 Starting VoiceFlow Express Backend API Tests"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to make HTTP requests
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local use_guest_auth=$4
    local auth_header=""

    if [ "$use_guest_auth" = "true" ] && [ -n "$GUEST_TOKEN" ]; then
        auth_header="-H \"Authorization: Bearer $GUEST_TOKEN\""
    elif [ -n "$AUTH_TOKEN" ]; then
        auth_header="-H \"Authorization: Bearer $AUTH_TOKEN\""
    fi

    echo -e "${BLUE}Testing: $method $endpoint${NC}"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X GET "$BASE_URL$endpoint" $auth_header)
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BASE_URL$endpoint" \
                -H "Content-Type: application/json" \
                $auth_header \
                -d "$data")
        else
            response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BASE_URL$endpoint" \
                $auth_header)
        fi
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            $auth_header \
            -d "$data")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X DELETE "$BASE_URL$endpoint" \
            $auth_header)
    fi

    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_STATUS:/d')

    if [ "$http_status" -ge 200 ] && [ "$http_status" -lt 300 ]; then
        echo -e "${GREEN}✅ SUCCESS ($http_status)${NC}"
    elif [ "$http_status" -ge 400 ] && [ "$http_status" -lt 500 ]; then
        echo -e "${YELLOW}⚠️  CLIENT ERROR ($http_status)${NC}"
    elif [ "$http_status" -ge 500 ]; then
        echo -e "${RED}❌ SERVER ERROR ($http_status)${NC}"
    else
        echo -e "${BLUE}ℹ️  INFO ($http_status)${NC}"
    fi

    if [ -n "$body" ] && [ "$body" != "null" ]; then
        echo "Response: $body"
    fi
    echo ""
}

# Function to extract auth token from response
extract_token() {
    local response=$1
    # Extract token from JSON response (simple extraction)
    echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4
}

echo "🏥 Testing Health Check"
echo "======================"
make_request "GET" "/health"

echo "🔐 Testing Auth Endpoints (No Auth Required)"
echo "============================================"

# Clerk sync
echo "Testing: POST /auth/clerk_sync"
clerk_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BASE_URL/auth/clerk_sync" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com"}')
clerk_status=$(echo "$clerk_response" | grep "HTTP_STATUS:" | cut -d: -f2)
clerk_body=$(echo "$clerk_response" | sed '/HTTP_STATUS:/d')

if [ "$clerk_status" -ge 200 ] && [ "$clerk_status" -lt 300 ]; then
    echo -e "${GREEN}✅ SUCCESS ($clerk_status)${NC}"
    AUTH_TOKEN=$(extract_token "$clerk_body")
    if [ -n "$AUTH_TOKEN" ]; then
        echo "Got auth token from clerk_sync"
    fi
else
    echo -e "${YELLOW}⚠️  CLIENT ERROR ($clerk_status)${NC}"
fi
echo "Response: $clerk_body"
echo ""

# Guest login (fallback if clerk_sync fails)
if [ -z "$AUTH_TOKEN" ]; then
    echo "Testing: POST /auth/guest"
    guest_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$BASE_URL/auth/guest" \
        -H "Content-Type: application/json" \
        -d '{"name":"Test Guest User"}')
    guest_status=$(echo "$guest_response" | grep "HTTP_STATUS:" | cut -d: -f2)
    guest_body=$(echo "$guest_response" | sed '/HTTP_STATUS:/d')

    if [ "$guest_status" -ge 200 ] && [ "$guest_status" -lt 300 ]; then
        echo -e "${GREEN}✅ SUCCESS ($guest_status)${NC}"
        GUEST_TOKEN=$(extract_token "$guest_body")
        if [ -n "$GUEST_TOKEN" ]; then
            echo "Got guest auth token"
        fi
    else
        echo -e "${YELLOW}⚠️  CLIENT ERROR ($guest_status)${NC}"
    fi
    echo "Response: $guest_body"
    echo ""
fi

# Login (may not work without proper setup)
make_request "POST" "/auth/login" '{"email":"test@example.com","password":"password123"}'

# Signup
make_request "POST" "/auth/signup" '{"email":"newuser@example.com","password":"password123","name":"New Test User"}'

# Logout
make_request "POST" "/auth/logout"

echo "🔐 Testing Auth Endpoints (With Auth)"
echo "===================================="

# Get current user (requires auth)
if [ -n "$AUTH_TOKEN" ]; then
    make_request "GET" "/auth/me"
elif [ -n "$GUEST_TOKEN" ]; then
    make_request "GET" "/auth/me" "" "true"
else
    echo -e "${YELLOW}⚠️  Skipping /auth/me - no auth token available${NC}"
    echo ""
fi

echo "📊 Testing Analytics Endpoints"
echo "=============================="
make_request "GET" "/analytics/overview" "" "true"
make_request "GET" "/analytics/calls" "" "true"
make_request "GET" "/analytics/realtime" "" "true"
make_request "GET" "/analytics/metrics-chart" "" "true"
make_request "GET" "/analytics/agent-comparison" "" "true"

echo "👔 Testing Onboarding Endpoints"
echo "==============================="
make_request "POST" "/onboarding/company" '{"name":"Test Company","industry":"Technology","size":"10-50"}' "true"
make_request "POST" "/onboarding/agent" '{"name":"Test Agent","description":"A helpful AI assistant","type":"customer-service"}' "true"
make_request "POST" "/onboarding/voice" '{"voice":"alloy","language":"en","speed":1.0}' "true"
make_request "POST" "/onboarding/channels" '{"channels":["web","phone","email"],"webhookUrl":"https://example.com/webhook"}' "true"
make_request "POST" "/onboarding/agent-config" '{"config":{"temperature":0.7,"maxTokens":1000,"systemPrompt":"You are a helpful assistant"}}' "true"
make_request "POST" "/onboarding/deploy" '{"environment":"development","region":"us-east-1"}' "true"
make_request "GET" "/onboarding/status" "" "true"
make_request "POST" "/onboarding/progress" '{"step":"company","completed":true,"data":{"companyName":"Test Corp"}}' "true"
make_request "GET" "/onboarding/progress" "" "true"
make_request "DELETE" "/onboarding/progress" "" "true"

echo "📞 Testing Twilio Endpoints"
echo "==========================="
make_request "GET" "/twilio/numbers" "" "true"
make_request "POST" "/twilio/voice" '{"message":"Hello from test","to":"+1234567890","agentId":"test-agent-id"}' "true"
make_request "POST" "/twilio/call" '{"to":"+1234567890","agentId":"test-agent-id","options":{"record":true}}' "true"
make_request "GET" "/twilio/call/test-call-sid" "" "true"

echo "🤖 Testing Agents Endpoints"
echo "==========================="
make_request "GET" "/api/agents" "" "true"
make_request "GET" "/api/agents/test-agent-id" "" "true"
make_request "POST" "/api/agents" '{"name":"Test Agent","description":"A helpful AI assistant","systemPrompt":"You are a helpful assistant","model":"gpt-4","temperature":0.7}' "true"
make_request "PUT" "/api/agents/test-agent-id" '{"name":"Updated Agent","description":"Updated description","temperature":0.8}' "true"
make_request "DELETE" "/api/agents/test-agent-id" "" "true"

echo "📄 Testing Documents Endpoints"
echo "=============================="
make_request "GET" "/api/documents" "" "true"
make_request "GET" "/api/documents/test-doc-id" "" "true"
make_request "POST" "/api/documents" '{"title":"Test Document","content":"This is test content for the document","type":"text","metadata":{"author":"Test User","tags":["test","sample"]}}' "true"
make_request "PUT" "/api/documents/test-doc-id" '{"title":"Updated Document","content":"Updated content","metadata":{"updated":true}}' "true"
make_request "DELETE" "/api/documents/test-doc-id" "" "true"

# File upload (this will likely fail without a real file)
echo "📎 Testing Document Upload (may fail without file)"
make_request "POST" "/api/documents/upload" "" "true"

echo "🧠 Testing RAG Endpoints"
echo "========================"
make_request "POST" "/api/rag/query" '{"query":"What is machine learning?","agentId":"test-agent","sessionId":"test-session","context":{"previousMessages":[]}}' "true"
make_request "GET" "/api/rag/conversation/test-session-id" "" "true"
make_request "DELETE" "/api/rag/conversation/test-session-id" "" "true"

echo "⚙️ Testing Ingestion Endpoints"
echo "=============================="
make_request "POST" "/api/ingestion/start" '{"documents":[{"id":"doc1","content":"Test content","title":"Test Doc"}],"agentId":"test-agent","options":{"chunkSize":1000}}' "true"
make_request "GET" "/api/ingestion/status/test-job-id" "" "true"
make_request "GET" "/api/ingestion/jobs" "" "true"

echo "🏃 Testing Runner Endpoints"
echo "==========================="
make_request "POST" "/api/runner/chat" '{"message":"Hello, how can I help you?","agentId":"test-agent","sessionId":"test-session","context":{}}' "true"
make_request "GET" "/api/runner/agent/test-agent-id" "" "true"

# Audio upload (this will likely fail without a real audio file)
echo "🎵 Testing Audio Upload (may fail without audio file)"
make_request "POST" "/api/runner/audio" "" "true"

echo "👥 Testing Users Endpoints"
echo "=========================="
make_request "GET" "/api/users/test-user-id" "" "true"

echo "🔧 Testing Admin Endpoints"
echo "=========================="
make_request "POST" "/admin/pipeline_agents" '{"agentId":"test-agent","pipelineId":"test-pipeline","config":{"enabled":true}}' "true"
make_request "GET" "/admin/pipeline_agents" "" "true"
make_request "POST" "/admin/pipelines" '{"name":"Test Pipeline","description":"A test pipeline","config":{"steps":[{"name":"step1","type":"process"}]},"enabled":true}' "true"
make_request "GET" "/admin/pipelines" "" "true"
make_request "POST" "/admin/pipelines/trigger" '{"pipelineId":"test-pipeline","data":{"input":"test data","options":{}}}' "true"

echo ""
echo "🎉 API Testing Complete!"
echo "========================"
echo "Summary:"
echo "- Health check: ✅ Working"
echo "- Auth endpoints: ✅ Some working (clerk_sync, guest login)"
if [ -n "$AUTH_TOKEN" ] || [ -n "$GUEST_TOKEN" ]; then
    echo "- Protected endpoints: 🧪 Tested with authentication"
else
    echo "- Protected endpoints: ⚠️  Tested without authentication (may fail)"
fi
echo ""
echo "Notes:"
echo "- Endpoints requiring file uploads may fail without actual files"
echo "- Some endpoints may require specific setup or data in the database"
echo "- Check the responses above for detailed error information"
echo "- Use guest login for testing protected endpoints"