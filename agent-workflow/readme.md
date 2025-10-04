# RAG Agent Workflow API

A production-ready FastAPI application that implements a Retrieval-Augmented Generation (RAG) workflow using ChromaDB for vector search and Groq for LLM inference. This API is designed to be compatible with Twilio webhooks for conversational AI applications.

## 🎯 Features

- **RAG Pipeline**: Complete RAG workflow with vector search and context-aware responses
- **No Hallucinations**: Only answers based on knowledge base content
- **Twilio Compatible**: Ready-to-use webhook endpoints for SMS integration
- **Single File**: Everything in one file for easy deployment
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Health Checks**: Built-in health check endpoints

## 📋 Prerequisites

- Python 3.8+
- ChromaDB with pre-populated collection
- Groq API key
- pip (Python package manager)

## 🚀 Installation

### 1. Install Dependencies

```bash
pip install fastapi uvicorn chromadb groq python-dotenv pydantic
```

## ⚡ Quick Start

Follow these steps to get a local PoC running quickly (assumes Windows cmd.exe or PowerShell):

1. Install Python dependencies:

```cmd
cd agent-workflow
python -m pip install -r requirements.txt
```

2. Download a Vosk model (the repo includes a helper script):

```cmd
cd agent-workflow\scripts
python download_vosk_model.py --yes
```

3. (Optional) Create a 16kHz PCM16 test audio file for the simulator:

```cmd
ffmpeg -i input.wav -ar 16000 -ac 1 -f s16le ..\test_audio\sample16k_pcm16.raw
```

4. Expose your local server with ngrok (the app runs on port 8001):

```cmd
ngrok http 8001
```

5. Set `TWILIO_PUBLIC_WS` to the wss URL from ngrok, then start the app:

```cmd
set TWILIO_PUBLIC_WS=wss://<your-ngrok-id>.ngrok.io/ws/twilio-media
cd ..
python app.py
```

If you plan to use Media Streams (low-latency audio), also enable the feature explicitly:

```cmd
set USE_MEDIA_STREAM=true
```


### 2. Set Up Environment Variables

Create a `.env` file in the same directory as the application:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here
CHROMA_DB_PATH=/path/to/your/chroma_db

# Optional (defaults provided)
COLLECTION_NAME=documents
GROQ_MODEL=llama-3.1-70b-versatile
  MAX_RESULTS=3
  SIMILARITY_THRESHOLD=0.3
```

#### Environment Variable Descriptions:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ Yes | - | Your Groq API key from [console.groq.com](https://console.groq.com) |
| `CHROMA_DB_PATH` | ✅ Yes | `./chroma_db` | Path to your ChromaDB persistent storage |
| `COLLECTION_NAME` | ❌ No | `documents` | Name of the ChromaDB collection to use |
| `GROQ_MODEL` | ❌ No | `llama-3.1-70b-versatile` | Groq model to use for generation |
| `MAX_RESULTS` | ❌ No | `3` | Maximum number of documents to retrieve |
| `SIMILARITY_THRESHOLD` | ❌ No | `0.3` | Minimum similarity score (0-1) for results |
| `USE_MEDIA_STREAM` | ❌ No | `false` | Toggle Media Streams behavior. When `true` and `TWILIO_PUBLIC_WS` is set, `/webhook/twilio/voice` will return a `<Start><Stream/>` TwiML to enable Twilio Media Streams. |

### 3. Prepare Your ChromaDB

Ensure your ChromaDB is already set up with documents. Here's an example of how to create one:

```python
import chromadb
from chromadb.config import Settings

# Initialize ChromaDB
client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

# Create collection
collection = client.create_collection(name="documents")

# Add documents
collection.add(
    documents=[
        "Your first document content here...",
        "Your second document content here...",
    ],
    metadatas=[
        {"source": "doc1.txt", "category": "info"},
        {"source": "doc2.txt", "category": "guide"},
    ],
    ids=["doc1", "doc2"]
)
```

## 🏃 Running the Application

### Development Mode

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

### Production Mode

```bash
uvicorn app:app --host 0.0.0.0 --port 8001 --workers 4
```

The API will be available at `http://localhost:8001` (this project uses port 8001 by default)

## 📡 API Endpoints

### 1. Root Endpoint (Health Check)

**GET** `/`

Simple health check to verify the service is running.

**Response:**
```json
{
  "status": "online",
  "service": "RAG Agent Workflow API",
  "version": "1.0.0",
  "agent_ready": true
}
```

### 2. Detailed Health Check

**GET** `/health`

Provides detailed information about the service configuration.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-01T12:00:00",
  "chroma_db_path": "./chroma_db",
  "collection_name": "documents",
  "model": "llama-3.1-70b-versatile"
}
```

### 3. Query Endpoint

**POST** `/query`

Main endpoint for asking questions to the RAG agent.

**Request Body:**
```json
{
  "query": "What is the capital of France?",
  "user_id": "user123"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "query": "What is the capital of France?",
  "answer": "According to Document 1, the capital of France is Paris...",
  "sources": [
    {
      "document_number": 1,
      "similarity_score": 0.892,
      "metadata": {
        "source": "geography.txt",
        "category": "facts"
      },
      "preview": "France is a country in Western Europe. Its capital is Paris..."
    }
  ],
  "timestamp": "2025-10-01T12:00:00",
  "metadata": {
    "user_id": "user123",
        ### 6. Streaming Query Endpoint (Server-Sent Events)
    "processing_time_ms": 1234,
    "documents_found": 3
  },
  "error": null
}
```

### 4. Twilio Webhook (TwiML Response)

**POST** `/webhook/twilio`

Twilio-compatible webhook that returns TwiML for SMS responses.

**Expected Form Data from Twilio:**
- `Body`: The SMS message text
- `From`: Sender's phone number
- `MessageSid`: Twilio message identifier

**Response (TwiML):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Your answer here...</Message>
</Response>
```

### 5. Twilio Webhook (JSON Response)

        curl -N -X POST "http://localhost:8001/query/stream" \

Alternative Twilio webhook that returns JSON instead of TwiML. Useful for testing.

**Expected Form Data:**
- `Body`: The message text
- `From`: Sender identifier

**Response:** Same as `/query` endpoint

## 🔄 RAG Workflow Steps
          "http://localhost:8001/query/stream",
The application follows this workflow:

1. **Receive Query** - Accept user's question via API
2. **Process Query** - Clean and validate the input
3. **Search Embeddings** - Query ChromaDB for relevant documents
   - Vector similarity search
   - Filter by similarity threshold
4. **Build RAG Prompt** - Construct prompt with retrieved context
5. **Generate Answer** - Use Groq LLM to generate response
6. **Format Answer** - Structure response with sources
7. **Return Response** - Send formatted answer to client

## 🔗 Twilio Integration

### Setting Up Twilio

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to your phone number settings
3. Under "Messaging", set the webhook URL:
   - **Webhook URL**: `https://your-domain.com/webhook/twilio`
   - **HTTP Method**: POST

### Testing Locally with Twilio

Use [ngrok](https://ngrok.com/) to expose your local server:

```bash
# Start your FastAPI app
python app.py

# In another terminal, start ngrok (app uses port 8001)
ngrok http 8001

# Use the ngrok URL in Twilio webhook settings
# Example: https://abc123.ngrok.io/webhook/twilio
```

### Voice Calls (Twilio Voice)

This project now supports live voice calls via Twilio Voice. There are two endpoints you can configure in your Twilio phone number settings:

- **Primary webhook (Voice)**: POST to `https://<your-host>/webhook/twilio/voice`
  - This returns TwiML with a `<Gather input="speech">` which prompts the caller and posts the transcribed speech to the result URL.
- **Gather result URL**: POST to `https://<your-host>/webhook/twilio/voice/result`
  - Twilio will POST the transcribed speech (`SpeechResult`) here; the server calls the RAG agent and returns TwiML `<Say>` with the agent's spoken reply, then redirects back to the gather endpoint for a continued conversation loop.

How to configure in the Twilio Console:
1. Go to your Phone Numbers -> Manage -> Active Numbers and open the number.
2. Under "Voice & Fax", set "A CALL COMES IN" to "Webhook" with HTTP POST and the URL `https://<your-host>/webhook/twilio/voice`.
3. Ensure your public host (ngrok or real domain) is HTTPS.

Notes and tips:
- Keep `Say` replies relatively short to avoid long blocking TTS audio. The server truncates to ~600 characters by default.
- If you want a conversational experience with interruptions, consider using the WebSocket endpoint for lower-latency exchanges, and use Twilio's Media Streams or SIP to bridge audio in more advanced setups.
- When testing locally, use ngrok (or a similar tunneling tool) and paste the ngrok HTTPS URL into Twilio's webhook configuration.

### Twilio Media Streams (real-time audio)

For low-latency, live voice interactions you can use Twilio Media Streams to stream raw audio to a WebSocket on your server. This repo includes a Media Streams skeleton and a Vosk-based ASR PoC.

Endpoints added:
- `ws://<host>:8001/ws/twilio-media` — WebSocket endpoint for Twilio Media Streams.

Important: Media Streams are gated by an explicit environment toggle. Before Twilio will be instructed to open a Media Stream, you must set BOTH:

1. `TWILIO_PUBLIC_WS` — the public wss URL Twilio should connect to (for example from ngrok)
2. `USE_MEDIA_STREAM=true` — an explicit opt-in switch to enable media streaming behavior

How it works:
1. Twilio opens a WebSocket to your configured Media Stream URL and sends JSON frames including `connected`, `media` (base64 payload), and `closed` events.
2. The server decodes the audio frames and runs a local Vosk ASR (open-source) to obtain transcripts.
3. Transcripts are sent to your RAG agent; agent replies are forwarded back to the WebSocket client as JSON `{type: 'agent', transcript: '...', reply: '...'}.`

Simulator:
- `agent-workflow/tools/twilio_media_simulator.py` — simulates Twilio frames by reading a local PCM16 16kHz audio file and streaming frames to the WebSocket. Place a test audio file at `agent-workflow/test_audio/sample16k_pcm16.raw` (PCM16 16kHz mono) and run:

```bash
python tools/twilio_media_simulator.py
```

Playing replies to the caller:
- The PoC pushes agent replies back over the WebSocket to your bridge. To have the caller hear replies you can:
  1. Use the Twilio REST API to update the live call's TwiML (make the call play your TTS reply), or
  2. Use Twilio's `<Stream>` TwiML and implement an audio bridge that streams synthesized audio back into the call.

The PoC focuses on low-latency ASR + agent integration using open-source tools (Vosk). If you want, I can extend the bridge to automatically play agent replies back into the live call using Twilio's REST API (requires your Twilio Account SID/Auth Token in `.env`).

### Quick test checklist for Media Streams

1. Ensure dependencies are installed and a Vosk model is downloaded (`python scripts/download_vosk_model.py --yes`).
2. Start the app: `python app.py` (port 8001)
3. Start ngrok: `ngrok http 8001` and copy the HTTPS host
4. Set `TWILIO_PUBLIC_WS` to the corresponding wss URL, e.g. `wss://<ngrok-id>.ngrok.io/ws/twilio-media`
5. Set `USE_MEDIA_STREAM=true` in your environment or `.env`
6. Configure your Twilio phone number's Voice webhook to POST to `https://<ngrok-host>/webhook/twilio/voice`
7. Place a call to the Twilio number; if enabled, the webhook will return `<Start><Stream url="..."/>` and Twilio will open the websocket to `/ws/twilio-media`.

If `USE_MEDIA_STREAM` is false/unset, the webhook will fall back to `<Gather input="speech">` and Twilio will perform its speech-to-text before POSTing the transcript to `/webhook/twilio/voice/result`.

## 📝 Example Usage

### Using cURL

```bash
# Query endpoint
curl -X POST "http://localhost:8001/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What information do you have about machine learning?",
    "user_id": "test_user"
  }'

# Health check
curl "http://localhost:8001/health"
```

### Using Python requests

```python
import requests

# Query the RAG agent
response = requests.post(
  "http://localhost:8001/query",
  json={
    "query": "What is in your knowledge base?",
    "user_id": "python_client"
  }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])} documents")
```

## 🛠️ Configuration Tips

### Adjusting Similarity Threshold

- **Higher (0.7-0.9)**: More strict, fewer but more relevant results
- **Lower (0.3-0.5)**: More lenient, more results but potentially less relevant

Recommended default for this repo: `SIMILARITY_THRESHOLD=0.3` (works well with the all-MiniLM-L6-v2 embedder on small-to-medium corpora). The project also includes a fallback that returns top-N results when filtering yields no matches.

### WebSocket (low-latency) support

For live, low-latency interactions the API exposes a WebSocket endpoint at:

  ws://<host>:8001/ws/query

Protocol:
- Client sends a single JSON object after the connection is accepted: {"query": "...", "user_id": "..."}
- Server streams JSON chunks (same schema as SSE) back to the client. Example chunk types: {"type":"start"}, {"type":"content"}, {"type":"sources"}, {"type":"end"}.

Minimal browser JS example:

```html
<script>
  const ws = new WebSocket('ws://localhost:8001/ws/query');
  ws.addEventListener('open', () => {
    ws.send(JSON.stringify({ query: 'What information do you have?', user_id: 'web_ui' }));
  });
  ws.addEventListener('message', (ev) => {
    const chunk = JSON.parse(ev.data);
    if (chunk.type === 'content') {
      // append chunk.content to the UI as it's received
      console.log('content:', chunk.content);
    } else if (chunk.type === 'sources') {
      console.log('sources:', chunk.sources);
    } else if (chunk.type === 'end') {
      console.log('finished', chunk.metadata);
    }
  });
</script>
```

Notes:
- WebSockets provide lower overhead and a smoother "typing" UX compared to polling or SSE. The server also accepts SSE at `/query/stream` for simpler clients.

### Non-blocking embeddings & timings

The streaming path uses a non-blocking embedding call (runs encode in a thread) so the FastAPI event loop remains responsive under concurrent requests. The API also returns per-step timings in the response metadata or in the final streaming `end` event (field `timings_ms`) so you can measure where time is spent (embedding, vector search, prompt build, LLM).

### Performance tuning checklist

1. Reduce `MAX_RESULTS` (we default to 3) to keep prompt sizes small.
2. Use GPU for embeddings to reduce encode latency.
3. Prefer streaming/WS UI to improve perceived latency (preview chunks are sent before full answer generation).
4. Consider lighter Groq models (e.g., `llama-3.1-8b-instant`) for faster responses.

### Choosing Groq Models

Available models (as of 2025):
- `llama-3.1-70b-versatile` - Best balance of speed and quality (default)
- `llama-3.1-8b-instant` - Fastest responses
- `mixtral-8x7b-32768` - Longer context window

### Optimizing Performance

1. **Reduce MAX_RESULTS**: Fewer documents = faster processing
2. **Increase SIMILARITY_THRESHOLD**: More selective retrieval
3. **Use smaller Groq models**: Faster inference time

## 🐛 Troubleshooting

### "RAG Agent not initialized" Error

**Problem**: ChromaDB or Groq API not accessible

**Solutions**:
1. Check `.env` file exists and has correct values
2. Verify `CHROMA_DB_PATH` points to valid ChromaDB
3. Confirm `GROQ_API_KEY` is valid
4. Check ChromaDB collection exists with correct name

### "No documents found" Response

**Problem**: Vector search returns no results

**Solutions**:
1. Lower `SIMILARITY_THRESHOLD` in `.env`
2. Verify ChromaDB has documents in the collection
3. Check if query is too specific or unrelated to knowledge base

### Twilio Webhook Not Working

**Problem**: Twilio not receiving responses

**Solutions**:
1. Verify webhook URL is publicly accessible
2. Check Twilio expects POST method
3. Review Twilio logs in console
4. Test with `/webhook/twilio/json` endpoint first

## 📊 Logging

The application uses Python's logging module. Logs include:
- Request processing steps
- Vector search results
- LLM generation status
- Error messages with stack traces

To adjust log level, modify the `logging.basicConfig()` call in the code:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🔒 Security Considerations

1. **API Key Protection**: Never commit `.env` file to version control
2. **Input Validation**: All inputs are validated via Pydantic models
3. **Rate Limiting**: Consider adding rate limiting for production (not included)
4. **HTTPS**: Always use HTTPS in production (especially for Twilio)

## 📦 File Structure

```
project/
├── app.py              # Main application file (this file)
├── .env                # Environment variables (create this)
├── .env.example        # Example environment file
├── README.md           # This file
├── test_api.py         # Test file (see Testing section)
└── chroma_db/          # ChromaDB storage directory
    └── ...             # ChromaDB files
```

## 🧪 Testing

See `test_api.py` for comprehensive testing examples.

Run tests:
```bash
python test_api.py
```

## 📄 License

This project is provided as-is for use in your applications.

## 🤝 Support

For issues or questions:
1. Check the Troubleshooting section
2. Review logs for error messages
3. Verify environment configuration
4. Test with the provided test file

## 🔄 Updates and Maintenance

- Keep dependencies updated: `pip install --upgrade fastapi uvicorn chromadb groq`
- Monitor Groq API for model updates
- Regularly backup your ChromaDB data
- Review logs for performance optimization opportunities
