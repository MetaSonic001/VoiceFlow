# VoiceFlow Twilio Voice Integration

This directory contains the Twilio voice integration for VoiceFlow, enabling phone-callable AI agents with real-time RAG (Retrieval-Augmented Generation) capabilities.

## Features

- **Real-time Voice Processing**: Handle incoming phone calls using Twilio TwiML `<Gather>` speech recognition
- **RAG-Powered Responses**: Generate contextually relevant responses using your document knowledge base with Groq Cloud (per-tenant BYOK key or platform fallback)
- **Natural Voice Synthesis**: Respond with Chatterbox TTS (self-hosted) or TwiML `<Say>` fallback
- **Per-tenant Credentials**: Each tenant stores their own AES-256-GCM encrypted Twilio keys
- **Multi-tenant Support**: Isolated voice agents per tenant and agent configuration

## Architecture

```
Phone Call → Twilio → POST /twilio/voice/incoming → TwiML <Gather> → caller speaks →
Twilio POST /twilio/voice/respond (SpeechResult) → 5-Layer Context Injection →
RAG retrieval → Policy scoring → Groq LLM → TwiML <Say> response → loop
```

## Setup Instructions

### 1. Prerequisites

- Node.js 18+
- Twilio account with a phone number
- Groq API key (optional — tenants can bring their own via Settings → Integrations)
- ngrok (for local development)

### 2. Environment Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Fill in your Twilio and Groq credentials:
   ```bash
   TWILIO_ACCOUNT_SID=your_account_sid        # optional — fallback if tenant has no creds
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+18283838255
   TWILIO_PHONE_NUMBER_SID=your_phone_number_sid
   GROQ_API_KEY=your_groq_api_key             # optional — tenants bring their own key
   TTS_SERVICE_URL=http://localhost:8003       # Chatterbox TTS microservice
   ```

### 3. Install Dependencies

```bash
npm install
```

### 4. Start the Server

```bash
npm run dev
```

### 5. Setup ngrok Tunnel

For local development, create a public tunnel to your server:

```bash
ngrok http 8000
```

### 6. Update Twilio Webhook

Use the provided script to automatically update your Twilio phone number webhook:

```bash
python scripts/update_twilio_webhook.py
```

This script will:
- Detect your ngrok URL
- Update your Twilio phone number's voice webhook URL
- Configure it to point to `/twilio/voice/incoming`

## API Endpoints

### Voice Incoming
- **URL**: `POST /twilio/voice/incoming`
- **Description**: Handles incoming Twilio voice calls
- **Returns**: TwiML `<Gather>` response that listens for speech

### Voice Respond
- **URL**: `POST /twilio/voice/respond`
- **Description**: Processes `SpeechResult` from Twilio, runs full RAG pipeline, returns TwiML `<Say>` + `<Gather>` loop
- **Auth**: Twilio webhook signature validation (per-tenant auth token)

### Call Status
- **URL**: `POST /twilio/voice/status`
- **Description**: Call status webhook — persists CallLog on call completion

## Voice Processing Flow

1. **Incoming Call**: Twilio sends webhook to `/twilio/voice/incoming`
2. **TwiML Gather**: Server returns TwiML `<Gather input="speech">` to capture caller speech
3. **Speech Result**: Twilio posts transcribed text (`SpeechResult`) to `/twilio/voice/respond`
4. **Tenant Groq Key**: `getTenantGroqKey()` resolves per-tenant encrypted key (or platform fallback)
5. **RAG Processing**: 5-layer context injection → vector retrieval → policy scoring → dynamic prompt assembly
6. **LLM Inference**: Groq API with per-tenant model selection via `resolveModel()` (4-model allowlist)
7. **TTS Response**: TwiML `<Say>` returns AI response; `<Gather>` loops for next turn
8. **Call End**: Status webhook saves CallLog with transcript, duration, sentiment

## Configuration

### Voice Agent Settings

Voice agents are configured through the VoiceFlow dashboard. Each agent can have:

- **System Prompt**: Personality and behavior instructions
- **LLM Model**: Per-agent model selection from 4 Groq production models
- **Token Limit**: Maximum response length (2K–32K)
- **Document Context**: Knowledge base for RAG responses
- **Phone Number**: Assigned Twilio number (purchased via dashboard)

## Troubleshooting

### Common Issues

1. **"No HTTPS tunnel found"**
   - Ensure ngrok is running: `ngrok http 8000`
   - Check ngrok status at [http://localhost:4040](http://localhost:4040)

2. **"Failed to update Twilio webhook"**
   - Verify Twilio credentials in `.env` or tenant settings
   - Check that phone number SID is correct
   - Ensure Twilio account has permissions

3. **"Webhook signature validation failed"**
   - Per-tenant Twilio auth tokens are decrypted at runtime; ensure `CREDENTIALS_ENCRYPTION_KEY` is set
   - Check that the webhook URL matches exactly what Twilio sends to

4. **Poor audio quality**
   - Check network connection stability
   - Twilio `<Gather>` uses their hosted speech recognition — quality is on Twilio's side

### Logs and Debugging

- Server logs show call connection/disconnection events
- RAG processing includes query and response logging
- Twilio webhook payloads are logged for debugging
- CallLog records persist full transcripts for review

## Security

- Twilio webhook signature validation per-tenant (auth token decrypted from `tenant.settings`)
- Rate limiting on voice endpoints
- Per-tenant AES-256-GCM encrypted credentials
- Groq API keys encrypted at rest per-tenant

## Support

For issues or questions:
- Check the main VoiceFlow documentation
- Review Twilio's voice API documentation
- Open an issue in the VoiceFlow repository