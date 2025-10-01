"""
RAG Agent Workflow API
A FastAPI-based RAG system with ChromaDB and Groq LLM
Compatible with Twilio webhooks
"""

import os
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from groq import Groq

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Agent Workflow API",
    description="A RAG-based agent that searches vector database and generates contextual answers",
    version="1.0.0"
)

# ========================
# Configuration
# ========================
class Config:
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "documents")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))

    @classmethod
    def validate(cls):
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        if not os.path.exists(cls.CHROMA_DB_PATH):
            raise ValueError(f"ChromaDB path not found: {cls.CHROMA_DB_PATH}")

# ========================
# Pydantic Models
# ========================
class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's question or query")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    stream: bool = Field(False, description="Enable streaming response")
    
class TwilioWebhookRequest(BaseModel):
    Body: str = Field(..., description="Message body from Twilio")
    From: Optional[str] = Field(None, description="Sender phone number")
    MessageSid: Optional[str] = Field(None, description="Twilio message ID")

class QueryResponse(BaseModel):
    success: bool
    query: str
    answer: Optional[str] = None
    sources: Optional[list] = None
    error: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

class StreamChunk(BaseModel):
    type: str  # "start", "content", "sources", "end", "error"
    content: Optional[str] = None
    sources: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# ========================
# RAG Agent Class
# ========================
class RAGAgent:
    def __init__(self):
        """Initialize the RAG Agent with ChromaDB and Groq client"""
        try:
            # Validate configuration
            Config.validate()
            
            # Initialize ChromaDB
            logger.info(f"Initializing ChromaDB at: {Config.CHROMA_DB_PATH}")
            self.chroma_client = chromadb.PersistentClient(
                path=Config.CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(
                    name=Config.COLLECTION_NAME
                )
                logger.info(f"Loaded collection: {Config.COLLECTION_NAME}")
            except Exception as e:
                logger.error(f"Collection not found: {e}")
                raise ValueError(f"Collection '{Config.COLLECTION_NAME}' not found in ChromaDB")
            
            # Initialize Groq client
            self.groq_client = Groq(api_key=Config.GROQ_API_KEY)
            logger.info("Groq client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Agent: {e}")
            raise
    
    def process_query(self, query: str) -> str:
        """
        Step 2: Process and clean the query
        """
        # Basic query processing - trim whitespace and validate
        processed = query.strip()
        if not processed:
            raise ValueError("Query cannot be empty")
        
        logger.info(f"Processed query: {processed}")
        return processed
    
    def search_embeddings(self, query: str) -> Dict[str, Any]:
        """
        Step 3: Search for relevant documents using vector similarity
        """
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=Config.MAX_RESULTS,
                include=["documents", "metadatas", "distances"]
            )
            
            # Check if we got any results
            if not results or not results['documents'][0]:
                logger.warning("No documents found in vector search")
                return {
                    "found": False,
                    "documents": [],
                    "metadatas": [],
                    "distances": []
                }
            
            # Filter by similarity threshold (distances are smaller = more similar)
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
            distances = results['distances'][0] if results['distances'] else [0] * len(documents)
            
            # Filter results by threshold
            filtered_results = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                # Lower distance = higher similarity
                if dist <= (1 - Config.SIMILARITY_THRESHOLD):
                    filtered_results.append({
                        "document": doc,
                        "metadata": meta,
                        "distance": dist
                    })
            
            if not filtered_results:
                logger.warning("No documents passed similarity threshold")
                return {
                    "found": False,
                    "documents": [],
                    "metadatas": [],
                    "distances": []
                }
            
            logger.info(f"Found {len(filtered_results)} relevant documents")
            return {
                "found": True,
                "documents": [r["document"] for r in filtered_results],
                "metadatas": [r["metadata"] for r in filtered_results],
                "distances": [r["distance"] for r in filtered_results]
            }
            
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            raise
    
    def build_rag_prompt(self, query: str, search_results: Dict[str, Any]) -> str:
        """
        Step 3.2: Build RAG prompt with context from search results
        """
        if not search_results["found"]:
            return None
        
        # Build context from retrieved documents
        context_parts = []
        for i, doc in enumerate(search_results["documents"], 1):
            context_parts.append(f"Document {i}:\n{doc}\n")
        
        context = "\n".join(context_parts)
        
        # Build the prompt
        prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided context.

Context from knowledge base:
{context}

Instructions:
1. Answer the question using ONLY information from the context above
2. If the context doesn't contain enough information to answer the question, say "I don't have enough information in my knowledge base to answer that question."
3. Do not make up or infer information that isn't explicitly in the context
4. Be concise and accurate
5. If you reference information, indicate which document it came from

Question: {query}

Answer:"""
        
        logger.info("RAG prompt built successfully")
        return prompt
    
    def generate_answer(self, prompt: str) -> str:
        """
        Step 3.3: Generate answer using Groq LLM (non-streaming)
        """
        if not prompt:
            return "I don't have enough information in my knowledge base to answer that question."
        
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based only on provided context. Never hallucinate or make up information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=Config.GROQ_MODEL,
                temperature=0.1,  # Low temperature for more factual responses
                max_tokens=1024,
                stream=False
            )
            
            answer = chat_completion.choices[0].message.content
            logger.info("Answer generated successfully")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer with Groq: {e}")
            raise
    
    def generate_answer_stream(self, prompt: str):
        """
        Step 3.3: Generate answer using Groq LLM with streaming
        Yields chunks of text as they're generated
        """
        if not prompt:
            yield "I don't have enough information in my knowledge base to answer that question."
            return
        
        try:
            stream = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based only on provided context. Never hallucinate or make up information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=Config.GROQ_MODEL,
                temperature=0.1,
                max_tokens=1024,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            
            logger.info("Streaming answer generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating streaming answer with Groq: {e}")
            yield f"\n\n[Error: {str(e)}]"
    
    def format_answer(self, answer: str, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Format the answer with metadata
        """
        formatted = {
            "answer": answer.strip(),
            "sources": []
        }
        
        # Add source information
        if search_results["found"]:
            for i, (doc, meta, dist) in enumerate(zip(
                search_results["documents"],
                search_results["metadatas"],
                search_results["distances"]
            ), 1):
                source = {
                    "document_number": i,
                    "similarity_score": round(1 - dist, 3),  # Convert distance to similarity
                    "metadata": meta,
                    "preview": doc[:200] + "..." if len(doc) > 200 else doc
                }
                formatted["sources"].append(source)
        
        return formatted
    
    def process(self, query: str, user_id: Optional[str] = None) -> QueryResponse:
        """
        Main workflow: Execute all steps (non-streaming)
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Receive query (already done)
            logger.info(f"[STEP 1] Received query: {query[:100]}...")
            
            # Step 2: Process query
            logger.info("[STEP 2] Processing query...")
            processed_query = self.process_query(query)
            
            # Step 3: Search embeddings
            logger.info("[STEP 3.1] Searching vector database...")
            search_results = self.search_embeddings(processed_query)
            
            # Check if we found relevant documents
            if not search_results["found"]:
                logger.warning("No relevant documents found")
                return QueryResponse(
                    success=True,
                    query=query,
                    answer="I don't have enough information in my knowledge base to answer that question. Please ask something related to the documents I have access to.",
                    sources=[],
                    timestamp=datetime.now().isoformat(),
                    metadata={
                        "user_id": user_id,
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                        "documents_found": 0
                    }
                )
            
            # Step 3.2: Build RAG prompt
            logger.info("[STEP 3.2] Building RAG prompt...")
            prompt = self.build_rag_prompt(processed_query, search_results)
            
            # Step 3.3: Generate answer
            logger.info("[STEP 3.3] Generating answer with LLM...")
            raw_answer = self.generate_answer(prompt)
            
            # Step 4: Format answer
            logger.info("[STEP 4] Formatting answer...")
            formatted = self.format_answer(raw_answer, search_results)
            
            # Step 5: Return response
            logger.info("[STEP 5] Returning response")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return QueryResponse(
                success=True,
                query=query,
                answer=formatted["answer"],
                sources=formatted["sources"],
                timestamp=datetime.now().isoformat(),
                metadata={
                    "user_id": user_id,
                    "processing_time_ms": processing_time,
                    "documents_found": len(search_results["documents"])
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return QueryResponse(
                success=False,
                query=query,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                metadata={"user_id": user_id}
            )
    
    async def process_stream(self, query: str, user_id: Optional[str] = None):
        """
        Main workflow with streaming: Execute all steps and stream the response
        Yields JSON chunks as Server-Sent Events
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Receive query
            logger.info(f"[STREAM] Received query: {query[:100]}...")
            
            # Send start event
            yield {
                "type": "start",
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Step 2: Process query
            logger.info("[STREAM] Processing query...")
            processed_query = self.process_query(query)
            
            # Step 3: Search embeddings
            logger.info("[STREAM] Searching vector database...")
            search_results = self.search_embeddings(processed_query)
            
            # Check if we found relevant documents
            if not search_results["found"]:
                logger.warning("No relevant documents found")
                yield {
                    "type": "content",
                    "content": "I don't have enough information in my knowledge base to answer that question. Please ask something related to the documents I have access to."
                }
                # Send an explicit empty sources event so clients expecting a sources event
                # always receive a consistent event stream format.
                yield {
                    "type": "sources",
                    "sources": []
                }
                yield {
                    "type": "end",
                    "metadata": {
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
                        "documents_found": 0
                    }
                }
                return
            
            # Step 3.2: Build RAG prompt
            logger.info("[STREAM] Building RAG prompt...")
            prompt = self.build_rag_prompt(processed_query, search_results)
            
            # Step 3.3: Stream answer generation
            logger.info("[STREAM] Streaming answer generation...")
            
            full_answer = ""
            # Emit an immediate (possibly empty) content chunk so clients receive
            # a 'content' event quickly and can measure time-to-first-byte even
            # when the LLM doesn't stream incrementally.
            yield {
                "type": "content",
                "content": ""
            }
            for chunk in self.generate_answer_stream(prompt):
                full_answer += chunk
                yield {
                    "type": "content",
                    "content": chunk
                }
            
            # Step 4: Send sources
            logger.info("[STREAM] Sending sources...")
            formatted = self.format_answer(full_answer, search_results)
            
            yield {
                "type": "sources",
                "sources": formatted["sources"]
            }
            
            # Step 5: Send completion event
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            yield {
                "type": "end",
                "metadata": {
                    "user_id": user_id,
                    "processing_time_ms": processing_time,
                    "documents_found": len(search_results["documents"])
                }
            }
            
            logger.info("[STREAM] Stream completed")
            
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }

# ========================
# Initialize Agent
# ========================
try:
    agent = RAGAgent()
    logger.info("RAG Agent initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RAG Agent: {e}")
    agent = None

# ========================
# API Endpoints
# ========================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "RAG Agent Workflow API",
        "version": "1.0.0",
        "agent_ready": agent is not None
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "chroma_db_path": Config.CHROMA_DB_PATH,
        "collection_name": Config.COLLECTION_NAME,
        "model": Config.GROQ_MODEL
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Main query endpoint for the RAG agent
    Supports both regular and streaming responses
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    logger.info(f"Received query from user: {request.user_id} (stream={request.stream})")
    
    # If streaming is requested, redirect to stream endpoint
    if request.stream:
        raise HTTPException(
            status_code=400, 
            detail="For streaming, use POST /query/stream endpoint"
        )
    
    response = agent.process(request.query, request.user_id)
    return response

@app.post("/query/stream")
async def query_stream_endpoint(request: QueryRequest):
    """
    Streaming query endpoint - returns Server-Sent Events (SSE)
    Provides real-time streaming of the LLM response
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    logger.info(f"Received streaming query from user: {request.user_id}")
    
    async def event_generator():
        """Generate SSE events"""
        try:
            async for chunk in agent.process_stream(request.query, request.user_id):
                # Convert dict to JSON and send as SSE
                yield {
                    "event": chunk["type"],
                    "data": json.dumps(chunk)
                }
        except Exception as e:
            logger.error(f"Error in stream generator: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "error": str(e)})
            }
    
    # Explicitly set media_type and disable buffering so clients receive SSE events promptly
    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/webhook/twilio")
async def twilio_webhook(request: Request):
    """
    Twilio-compatible webhook endpoint
    Accepts form data from Twilio and returns TwiML response
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        message_body = form_data.get("Body", "")
        from_number = form_data.get("From", "")
        message_sid = form_data.get("MessageSid", "")
        
        logger.info(f"Twilio webhook received from {from_number}: {message_body[:100]}")
        
        # Process the query
        response = agent.process(message_body, from_number)
        
        # Return TwiML response
        if response.success and response.answer:
            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response.answer}</Message>
</Response>"""
        else:
            error_msg = response.error or "Sorry, I couldn't process your request."
            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{error_msg}</Message>
</Response>"""
        
        return JSONResponse(
            content=twiml_response,
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}")
        error_twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Sorry, an error occurred while processing your message.</Message>
</Response>"""
        return JSONResponse(
            content=error_twiml,
            media_type="application/xml"
        )

@app.post("/webhook/twilio/json")
async def twilio_webhook_json(request: Request):
    """
    Alternative Twilio webhook endpoint that returns JSON instead of TwiML
    Useful for testing and debugging
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="RAG Agent not initialized")
    
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        message_body = form_data.get("Body", "")
        from_number = form_data.get("From", "")
        
        logger.info(f"Twilio JSON webhook received from {from_number}")
        
        # Process the query
        response = agent.process(message_body, from_number)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing Twilio JSON webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================
# Run the application
# ========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
