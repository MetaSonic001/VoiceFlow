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
