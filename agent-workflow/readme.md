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

### 2. Set Up Environment Variables

Create a `.env` file in the same directory as the application:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here
CHROMA_DB_PATH=/path/to/your/chroma_db

# Optional (defaults provided)
COLLECTION_NAME=documents
GROQ_MODEL=llama-3.1-70b-versatile
MAX_RESULTS=5
SIMILARITY_THRESHOLD=0.5
```

#### Environment Variable Descriptions:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ Yes | - | Your Groq API key from [console.groq.com](https://console.groq.com) |
| `CHROMA_DB_PATH` | ✅ Yes | `./chroma_db` | Path to your ChromaDB persistent storage |
| `COLLECTION_NAME` | ❌ No | `documents` | Name of the ChromaDB collection to use |
| `GROQ_MODEL` | ❌ No | `llama-3.1-70b-versatile` | Groq model to use for generation |
| `MAX_RESULTS` | ❌ No | `5` | Maximum number of documents to retrieve |
| `SIMILARITY_THRESHOLD` | ❌ No | `0.5` | Minimum similarity score (0-1) for results |

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
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

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

**POST** `/webhook/twilio/json`

Alternative Twilio webhook that returns JSON instead of TwiML. Useful for testing.

**Expected Form Data:**
- `Body`: The message text
- `From`: Sender identifier

**Response:** Same as `/query` endpoint

## 🔄 RAG Workflow Steps

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

# In another terminal, start ngrok
ngrok http 8000

# Use the ngrok URL in Twilio webhook settings
# Example: https://abc123.ngrok.io/webhook/twilio
```

## 📝 Example Usage

### Using cURL

```bash
# Query endpoint
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What information do you have about machine learning?",
    "user_id": "test_user"
  }'

# Health check
curl "http://localhost:8000/health"
```

### Using Python requests

```python
import requests

# Query the RAG agent
response = requests.post(
    "http://localhost:8000/query",
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
