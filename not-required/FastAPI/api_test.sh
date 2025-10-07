#!/bin/bash

# Simple VoiceFlow AI API Testing (No jq required)
# Run this step by step to test your API

API_BASE="http://localhost:8000"

echo "🚀 VoiceFlow AI API Testing (Simple Version)"
echo "=============================================="

# Function to extract token from response (basic grep/sed approach)
extract_token() {
    echo "$1" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4
}

extract_field() {
    local response="$1"
    local field="$2"
    echo "$response" | grep -o "\"$field\":\"[^\"]*" | cut -d'"' -f4
}

echo "📋 Step 1: Health Check"
echo "------------------------"
HEALTH_RESPONSE=$(curl -s -X GET "$API_BASE/health")
echo "Response: $HEALTH_RESPONSE"

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo "✅ API is running"
else
    echo "❌ API not responding properly"
    echo "Make sure FastAPI server is running on port 8000"
    exit 1
fi

echo ""
echo "🔐 Step 2: User Signup"
echo "------------------------"
SIGNUP_RESPONSE=$(curl -s -X POST "$API_BASE/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@company.com",
    "password": "password123",
    "company_name": "Test Company",
    "industry": "Technology"
  }')

echo "Signup Response: $SIGNUP_RESPONSE"

# Extract token using basic string manipulation
TOKEN=$(extract_token "$SIGNUP_RESPONSE")
USER_ID=$(extract_field "$SIGNUP_RESPONSE" "user_id")

echo "Extracted Token: $TOKEN"
echo "Extracted User ID: $USER_ID"

if [ -z "$TOKEN" ] || [ "$TOKEN" = "" ]; then
    echo "❌ Failed to get token from signup. Check API server logs."
    echo "Trying login instead..."
    
    LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "test@company.com",
        "password": "password123"
      }')
    
    echo "Login Response: $LOGIN_RESPONSE"
    TOKEN=$(extract_token "$LOGIN_RESPONSE")
    echo "Login Token: $TOKEN"
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "" ]; then
    echo "❌ No valid token available. Stopping tests."
    exit 1
fi

echo ""
echo "🔑 Step 3: Test Authentication"
echo "-------------------------------"
AUTH_RESPONSE=$(curl -s -X GET "$API_BASE/auth/me" \
  -H "Authorization: Bearer $TOKEN")
echo "Auth Response: $AUTH_RESPONSE"

if [[ $AUTH_RESPONSE == *"email"* ]]; then
    echo "✅ Authentication working"
else
    echo "❌ Authentication failed"
fi

echo ""
echo "📚 Step 4: Upload Knowledge (Text)"
echo "----------------------------------"
KNOWLEDGE_RESPONSE=$(curl -s -X POST "$API_BASE/onboarding/knowledge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text_content": "Our company provides AI-powered voice agents for businesses. We offer 24/7 customer support, lead qualification, and appointment scheduling services. Our pricing starts at $99/month for basic plans. For technical support, contact support@company.com or call 1-800-SUPPORT."
  }')

echo "Knowledge Response: $KNOWLEDGE_RESPONSE"

if [[ $KNOWLEDGE_RESPONSE == *"Knowledge uploaded"* ]] || [[ $KNOWLEDGE_RESPONSE == *"documents"* ]]; then
    echo "✅ Knowledge upload working"
else
    echo "⚠️ Knowledge upload may have issues"
fi

echo ""
echo "🤖 Step 5: Create Agent"
echo "------------------------"
AGENT_RESPONSE=$(curl -s -X POST "$API_BASE/onboarding/agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support Bot",
    "role": "customer_support",
    "channels": ["phone", "chat", "whatsapp"]
  }')

echo "Agent Response: $AGENT_RESPONSE"
AGENT_ID=$(extract_field "$AGENT_RESPONSE" "agent_id")
echo "Agent ID: $AGENT_ID"

echo ""
echo "💬 Step 6: Login for Session (Get Session ID)"
echo "----------------------------------------------"
SESSION_LOGIN=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@company.com",
    "password": "password123"
  }')

echo "Session Login Response: $SESSION_LOGIN"
SESSION_ID=$(extract_field "$SESSION_LOGIN" "session_id")
echo "Session ID: $SESSION_ID"

if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "" ]; then
    echo ""
    echo "💬 Step 7: Test Conversation"
    echo "-----------------------------"
    CONV_RESPONSE=$(curl -s -X POST "$API_BASE/conversations/$SESSION_ID/message" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "content": "What is your refund policy?",
        "type": "text"
      }')
    
    echo "Conversation Response: $CONV_RESPONSE"
    
    if [[ $CONV_RESPONSE == *"response"* ]]; then
        echo "✅ Conversation working"
    else
        echo "⚠️ Conversation may have issues"
    fi
    
    echo ""
    echo "💬 Step 8: Another Test Message"
    echo "--------------------------------"
    CONV2_RESPONSE=$(curl -s -X POST "$API_BASE/conversations/$SESSION_ID/message" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "content": "How can I contact support?",
        "type": "text"
      }')
    
    echo "Second Conversation Response: $CONV2_RESPONSE"
else
    echo "❌ No session ID available, skipping conversation tests"
fi

echo ""
echo "📊 Step 9: Test Analytics"
echo "-------------------------"
ANALYTICS_RESPONSE=$(curl -s -X GET "$API_BASE/analytics/overview" \
  -H "Authorization: Bearer $TOKEN")
echo "Analytics Response: $ANALYTICS_RESPONSE"

echo ""
echo "🤖 Step 10: Get All Agents"
echo "---------------------------"
AGENTS_RESPONSE=$(curl -s -X GET "$API_BASE/agents" \
  -H "Authorization: Bearer $TOKEN")
echo "Agents Response: $AGENTS_RESPONSE"

echo ""
echo "📋 Step 11: Get Call Logs"
echo "--------------------------"
LOGS_RESPONSE=$(curl -s -X GET "$API_BASE/calls/logs" \
  -H "Authorization: Bearer $TOKEN")
echo "Logs Response: $LOGS_RESPONSE"

echo ""
echo "🎉 Testing Complete!"
echo "===================="

# Summary
echo ""
echo "📋 SUMMARY:"
echo "-----------"

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo "✅ API Server: Running"
else
    echo "❌ API Server: Issues"
fi

if [[ $AUTH_RESPONSE == *"email"* ]]; then
    echo "✅ Authentication: Working"
else
    echo "❌ Authentication: Issues"
fi

if [[ $KNOWLEDGE_RESPONSE == *"Knowledge uploaded"* ]] || [[ $KNOWLEDGE_RESPONSE == *"documents"* ]]; then
    echo "✅ Knowledge Upload: Working"
else
    echo "⚠️ Knowledge Upload: Check logs"
fi

if [ -n "$SESSION_ID" ] && [ "$SESSION_ID" != "" ]; then
    echo "✅ Session Creation: Working"
    if [[ $CONV_RESPONSE == *"response"* ]]; then
        echo "✅ CrewAI Conversation: Working"
    else
        echo "⚠️ CrewAI Conversation: Check logs"
    fi
else
    echo "❌ Session Creation: Issues"
fi

echo ""
echo "🔧 If you see issues:"
echo "1. Check FastAPI server logs for errors"
echo "2. Make sure all Python dependencies are installed"
echo "3. Check if database file 'voiceflow.db' was created"
echo "4. Try resetting the database if needed"