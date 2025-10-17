# Complete VoiceFlow Demo

This script provides a complete end-to-end demonstration of the VoiceFlow platform, from URL content extraction to phone-callable agent setup.

## Features

- **URL Content Extraction**: Extracts content from any URL using the document ingestion service
- **ChromaDB Storage**: Stores extracted content with embeddings in ChromaDB
- **Agent Workflow**: Sets up a RAG agent that can answer questions about the extracted content
- **Twilio Integration**: Configures Twilio webhooks for phone calling
- **VOSK Speech Recognition**: Enables voice conversations with the agent

## Prerequisites

1. All VoiceFlow services running:
   - Backend API (port 8000)
   - Document Ingestion (port 8002)
   - Agent Workflow (port 8001)

2. Environment variables configured in `.env` file:

```bash
# Service URLs
BACKEND_URL=http://localhost:8000
INGESTION_URL=http://localhost:8002
AGENT_WORKFLOW_URL=http://localhost:8001

# Twilio (optional, for phone calling)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+18283838255

# Demo configuration
DEMO_TENANT_NAME="VoiceFlow Demo Tenant"
DEMO_AGENT_NAME="voiceflow-demo-agent"
```

## Installation

```bash
pip install -r demo_requirements.txt
```

## Usage

### Basic Usage (without phone calling)

```bash
python complete_demo.py https://example.com
```

### With Phone Calling Support

1. Configure Twilio credentials in your `.env` file
2. Run the demo:

```bash
python complete_demo.py https://example.com
```

3. Call the displayed phone number to interact with the agent

### Skip Twilio Setup

If you want to skip Twilio setup and just test the content extraction and agent workflow:

```bash
python complete_demo.py https://example.com --skip-twilio
```

## What It Does

1. **Service Health Check**: Verifies all required services are running
2. **Tenant & Agent Creation**: Creates a new tenant and agent in the backend
3. **Content Extraction**: Uploads the URL to the backend for processing
4. **Embedding Wait**: Waits for the document ingestion service to create embeddings
5. **Agent Testing**: Tests the agent workflow with a sample question
6. **Twilio Setup**: Configures Twilio webhooks and ngrok tunnel for phone calling
7. **Phone Number Display**: Shows the phone number you can call to test the agent

## Output

The script provides detailed logging of each step and displays:

- Tenant ID and Agent ID created
- Document ID for the extracted content
- Phone number for calling (if Twilio configured)
- Success/failure status of each step

## Troubleshooting

- **Services not running**: Ensure all three services are started before running the demo
- **Twilio setup fails**: Check your Twilio credentials and ensure ngrok is available
- **Embeddings timeout**: The script waits up to 5 minutes for embeddings; complex pages may take longer
- **Agent not responding**: Check the agent workflow logs for errors

## Example Output

```bash
🚀 Starting Complete VoiceFlow Demo
📋 Target URL: https://example.com
✅ Backend service is healthy
✅ Ingestion service is healthy
✅ Agent Workflow service is healthy
📝 Step 1: Creating tenant and agent
📤 Step 2: Uploading URL for content extraction
⏳ Step 3: Waiting for content extraction and embeddings
🧠 Step 4: Testing agent workflow
📞 Step 5: Setting up Twilio integration
🎉 Demo completed successfully!
📊 Summary: {'tenant_id': '...', 'agent_id': '...', 'document_id': '...', 'phone_number': '+18283838255'}

🎯 CALL THIS NUMBER TO TEST: +18283838255
The agent is now ready to answer questions about the extracted content!
``` 
