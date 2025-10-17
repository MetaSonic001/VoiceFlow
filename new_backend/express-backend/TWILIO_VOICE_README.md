# VoiceFlow Twilio Voice Integration

This directory contains the Twilio voice integration for VoiceFlow, enabling phone-callable AI agents with real-time RAG (Retrieval-Augmented Generation) capabilities.

## Features

- **Real-time Voice Processing**: Handle incoming phone calls with live speech recognition using Vosk (open-source)
- **RAG-Powered Responses**: Generate contextually relevant responses using your document knowledge base with Groq Cloud
- **Natural Voice Synthesis**: Convert AI responses to speech using Coqui TTS (open-source and free)
- **WebSocket Streaming**: Low-latency audio streaming for real-time conversation
- **Multi-tenant Support**: Isolated voice agents per tenant and agent configuration

## Architecture

```
Phone Call → Twilio → Webhook → Socket.IO → Vosk ASR → RagService (Groq) → VoiceService (Coqui TTS) → Response
```

## Setup Instructions

### 1. Prerequisites

- Node.js 18+
- Twilio account with a phone number
- OpenAI API key
- Vosk speech recognition model
- ngrok (for local development)

### 2. Environment Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Fill in your Twilio and Groq credentials:
   ```bash
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+18283838255
   TWILIO_PHONE_NUMBER_SID=your_phone_number_sid
   GROQ_API_KEY=your_groq_api_key
   ```

### 3. Install Dependencies

```bash
npm install
```

### 4. Download Vosk Model

```bash
# Create models directory
mkdir -p models

# Download English Vosk model (or your preferred language)
cd models
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip
unzip vosk-model-en-us-0.22.zip
mv vosk-model-en-us-0.22 vosk-model
```

### 5. Start the Server

```bash
npm run dev
```

### 6. Setup ngrok Tunnel

For local development, create a public tunnel to your server:

```bash
# Install ngrok if not already installed
npm install -g ngrok

# Start ngrok tunnel (server runs on port 3000)
ngrok http 3000
```

### 7. Update Twilio Webhook

Use the provided script to automatically update your Twilio phone number webhook:

```bash
python scripts/update_twilio_webhook.py
```

This script will:
- Detect your ngrok URL
- Update your Twilio phone number's voice webhook URL
- Configure it to point to `/api/twilio/voice`

## API Endpoints

### Voice Webhook
- **URL**: `POST /api/twilio/voice`
- **Description**: Handles incoming Twilio voice calls
- **Returns**: TwiML response directing Twilio to stream audio

### Media Stream
- **URL**: `WebSocket /media-stream`
- **Description**: Real-time audio streaming for speech processing
- **Protocol**: Socket.IO

### Outbound Calls
- **URL**: `POST /api/twilio/call`
- **Body**:
  ```json
  {
    "to": "+18283838255",
    "agentId": "voice-agent"
  }
  ```
- **Description**: Initiate outbound voice calls

### Call Status
- **URL**: `GET /api/twilio/call/:callSid`
- **Description**: Get status of a specific call

## Voice Processing Flow

1. **Incoming Call**: Twilio sends webhook to `/api/twilio/voice`
2. **TwiML Response**: Server returns TwiML to connect to WebSocket stream
3. **Audio Streaming**: Twilio streams audio in real-time via Socket.IO
4. **Speech Recognition**: Vosk processes audio chunks into text transcriptions (open-source)
5. **RAG Processing**: Transcriptions are sent to RagService for context-aware responses using Groq Cloud
6. **Text-to-Speech**: AI responses are converted to audio using Coqui TTS (open-source)
7. **Audio Response**: Synthesized speech is streamed back to the caller

## Configuration

### Voice Agent Settings

Voice agents are configured through the main VoiceFlow interface. Each agent can have:

- **System Prompt**: Personality and behavior instructions
- **Token Limit**: Maximum response length
- **Document Context**: Knowledge base for RAG responses

### Audio Settings

- **Sample Rate**: 16kHz (optimal for speech recognition)
- **Audio Format**: Linear PCM
- **Chunk Size**: 100ms audio buffers for low latency
- **Vosk Model**: English US model (open-source speech recognition)
- **TTS Engine**: Coqui TTS (open-source and free text-to-speech)
- **ASR Engine**: Vosk (open-source speech recognition)

## Troubleshooting

### Common Issues

1. **"No HTTPS tunnel found"**
   - Ensure ngrok is running: `ngrok http 3000`
   - Check ngrok status at [http://localhost:4040](http://localhost:4040)

2. **"Failed to update Twilio webhook"**
   - Verify Twilio credentials in `.env`
   - Check that phone number SID is correct
   - Ensure Twilio account has permissions

3. **"Vosk model not found"**
   - Download and extract Vosk model to `./models/vosk-model`
   - Verify `VOSK_MODEL_PATH` in environment

4. **Poor audio quality**
   - Check network connection stability
   - Verify sample rate compatibility
   - Monitor WebSocket connection health

### Logs and Debugging

- Server logs show call connection/disconnection events
- WebSocket events are logged for audio streaming
- RAG processing includes query and response logging
- Twilio webhook payloads are logged for debugging

## Security Considerations

- Webhook validation should be implemented in production
- Rate limiting on voice endpoints
- Input sanitization for all audio processing
- Secure storage of API keys and credentials

## Production Deployment

For production deployment:

1. Use a static IP or domain instead of ngrok
2. Implement webhook signature validation
3. Add monitoring and alerting
4. Configure load balancing for high availability
5. Set up proper SSL certificates
6. Implement call recording and analytics (optional)

## Support

For issues or questions:
- Check the main VoiceFlow documentation
- Review Twilio's voice API documentation
- Open an issue in the VoiceFlow repository