# FR CRCE Voice Information System

A comprehensive voice-based information system for FR CRCE college that allows prospective students and parents to call and get information about admissions, fees, courses, placements, and facilities.

## System Overview

This system consists of four main components:

1. **Knowledge Base Setup** - Creates a ChromaDB vector database with FR CRCE information
2. **Voice Agent (Flask App)** - Handles Twilio voice calls and provides RAG-based responses
3. **WebSocket Server** - Processes conversations and provides real-time analytics
4. **Twilio Setup** - Configures phone numbers and webhooks

## Prerequisites

### Software Requirements
- Python 3.8+
- Node.js 16+
- ngrok (for webhook tunneling)

### API Keys Required
- **Twilio Account** (Account SID and Auth Token)
- **Groq API Key** (for LLM responses)
- **Google Gemini API Key** (for conversation analysis)

### Python Dependencies
```bash
pip install flask twilio python-dotenv chromadb requests groq chromadb-client
```

### Node.js Dependencies
```bash
npm install express ws body-parser dotenv @google/generative-ai cors
```

## Setup Instructions

### Step 1: Environment Configuration

Create a `.env` file in your project root:

```env
# Twilio Credentials
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token

# Groq API (for voice responses)
GROQ_API_KEY=your_groq_api_key

# Google Gemini API (for conversation analysis)
GEMINI_API_KEY=your_google_gemini_api_key

# Optional: Server port
PORT=8080
```

### Step 2: Knowledge Base Setup

Run the knowledge base setup script to create the ChromaDB vector database:

```bash
python knowledgebase_setup.py
```

This script will:
- Create a `./chroma_db` directory
- Initialize the ChromaDB collection with FR CRCE information
- Add comprehensive knowledge about admissions, fees, courses, placements
- Test the knowledge base with sample queries

**Expected Output:**
```
Added 100+ documents to the enhanced FR CRCE knowledge base
✓ Multiple phrasings for same information
✓ Dynamic query keyword matching
✓ Priority-based retrieval
Ready for production RAG voice agent!
```

### Step 3: Start the WebSocket Server

In a new terminal, start the conversation analysis server:

```bash
node server.js
```

**Expected Output:**
```
FR CRCE Information System WebSocket Server running on port 8080
WebSocket endpoints:
- Dashboard: ws://localhost:8080?type=dashboard
- Admission Officers: ws://localhost:8080?type=admission-officer
- Analytics: ws://localhost:8080?type=analytics
HTTP endpoints:
- Webhook: http://localhost:8080/twilio-webhook
- Analytics: http://localhost:8080/analytics
- Health: http://localhost:8080/health
```

### Step 4: Configure Twilio and Start Voice Agent

Run the Twilio setup script:

```bash
python twilio_setup.py
```

This script will:
- Check all prerequisites (environment variables, knowledge base)
- Start ngrok tunnel for webhook access
- Configure your Twilio phone number
- Provide setup completion details

**Expected Output:**
```
FR CRCE College Information System - Twilio Setup
==================================================
✓ Environment and knowledge base checks passed
✓ Ngrok tunnel established: https://abc123.ngrok.io
✓ Successfully configured +18283838255

🎉 Setup Complete!
📞 Phone Number: +18283838255
🌐 Webhook URL: https://abc123.ngrok.io/voice
```

### Step 5: Start the Voice Agent

In another terminal, start the Flask application:

```bash
python app.py
```

**Expected Output:**
```
Starting FR CRCE Information System on port 5000
Make sure to use the HTTPS URL from ngrok for your Twilio webhook
Test the system at: http://localhost:5000/test
```

## Testing the System

### 1. Voice Testing
Call the phone number provided by the Twilio setup script and ask questions like:
- "What is the fee structure for B.Tech?"
- "How are the placements at FR CRCE?"
- "What courses do you offer?"
- "Where is the college located?"

### 2. Web Testing
Visit `http://localhost:5000/test` to test the system without making a phone call.

### 3. Analytics Dashboard
Check `http://localhost:8080/analytics` to view conversation analytics and statistics.

### 4. Health Checks
- Voice Agent: `http://localhost:5000/health`
- WebSocket Server: `http://localhost:8080/health`

## File Structure

```
frcrce-voice-system/
├── .env                          # Environment variables
├── knowledgebase_setup.py        # ChromaDB setup with FR CRCE data
├── app.py                        # Flask voice agent application
├── twilio_setup.py              # Twilio configuration script
├── server.js                     # WebSocket server for analytics
├── chroma_db/                    # ChromaDB vector database
├── package.json                  # Node.js dependencies
└── README.md                     # This file
```

## API Endpoints

### Voice Agent (Flask - Port 5000)
- `POST /voice` - Twilio webhook entry point
- `POST /process_speech` - Speech processing endpoint
- `GET/POST /test` - Web testing interface
- `GET /health` - Health check

### WebSocket Server (Node.js - Port 8080)
- `POST /twilio-webhook` - Receives conversation data
- `GET /analytics` - Daily statistics and metrics
- `GET /conversations` - List all conversations with filters
- `GET /conversation/:id` - Get specific conversation
- `GET /health` - Server health status

### WebSocket Connections
- `ws://localhost:8080?type=dashboard` - Real-time dashboard updates
- `ws://localhost:8080?type=admission-officer` - Urgent inquiry alerts
- `ws://localhost:8080?type=analytics` - Analytics data stream

## Configuration Options

### Voice Agent Configuration (app.py)
- **GROQ_MODEL**: Default "llama-3.1-8b-instant"
- **Session timeout**: Automatic after inactivity
- **Speech timeout**: 3 seconds for voice input
- **Language**: "en-IN" (English - India)

### Knowledge Base Configuration (knowledgebase_setup.py)
- **Collection name**: "frcrce_knowledge"
- **Document count**: 100+ comprehensive documents
- **Categories**: location, fees, admission, academics, placements, facilities
- **Embedding function**: Default ChromaDB embeddings

### Server Configuration (server.js)
- **AI Model**: "gemini-1.5-flash"
- **Analytics tracking**: Real-time conversation metrics
- **Client types**: Dashboard, admission officers, analytics
- **Storage**: In-memory (conversation history)

## Troubleshooting

### Common Issues

**1. "Knowledge base not found" error**
```bash
# Solution: Run the knowledge base setup
python knowledgebase_setup.py
```

**2. "GROQ_API_KEY not set" error**
```bash
# Solution: Add to .env file
echo "GROQ_API_KEY=your_api_key" >> .env
```

**3. "ngrok command not found" error**
```bash
# Solution: Install ngrok
# Windows: Download from https://ngrok.com/download
# macOS: brew install ngrok
# Linux: Download and extract to /usr/local/bin/
```

**4. Twilio webhook not receiving calls**
- Ensure ngrok is running and showing HTTPS URL
- Check Twilio console for webhook configuration
- Verify phone number is properly configured

**5. WebSocket connection failures**
```bash
# Check if server is running
curl http://localhost:8080/health

# Check WebSocket endpoint
wscat -c "ws://localhost:8080?type=dashboard"
```

### Debugging Tips

1. **Enable verbose logging**: Set `debug=True` in Flask app
2. **Check ChromaDB**: Use `/test` endpoint to verify knowledge base
3. **Monitor logs**: Watch terminal outputs for error messages
4. **Test APIs**: Use curl or Postman to test webhook endpoints

## Production Deployment

### Security Considerations
- Use environment variables for all API keys
- Enable HTTPS for all webhook URLs
- Implement rate limiting for API endpoints
- Add authentication for dashboard access

### Scaling Options
- Use Redis for session storage instead of in-memory
- Deploy on cloud platforms (Heroku, AWS, GCP)
- Use managed ChromaDB (Chroma Cloud)
- Implement load balancing for multiple instances

### Monitoring
- Set up logging aggregation (ELK stack, CloudWatch)
- Monitor API response times and error rates
- Track conversation satisfaction scores
- Alert on failed webhook deliveries

## Support and Maintenance

### Regular Tasks
- Update knowledge base with new college information
- Monitor and respond to urgent inquiries
- Review conversation analytics for system improvements
- Update API keys before expiration

### Getting Help
- Check logs for error messages
- Test individual components separately
- Verify all environment variables are set
- Ensure all prerequisites are installed

## License

This project is designed for educational purposes and internal use by FR CRCE college.

---

For technical support or questions about the system, contact the development team or refer to the troubleshooting section above.