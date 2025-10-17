# General Voice RAG Agent - Main Application
# app.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, Response, jsonify, redirect
import os
import json
import chromadb
import requests
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from twilio.twiml.voice_response import VoiceResponse, Gather
from chromadb import HttpClient
import time
import google.generativeai as genai
from groq import Groq
from typing import Dict, List, Any, Optional
import pandas as pd
from loguru import logger
import sqlite3
import re
from textblob import TextBlob
import threading
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

@app.before_request
def before_request():
    """Force HTTPS for cloudflared"""
    if 'trycloudflare.com' in request.host and request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast model for quicker responses
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")

# Initialize AI clients (prefer Groq for speed as primary)
groq_client = None
gemini_model = None

if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized as primary (faster)")
    except Exception as e:
        logger.error(f"Failed to initialize Groq: {str(e)}")
        print("⚠️ Check GROQ_API_KEY on Groq console")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(
            'gemini-2.0-flash-lite',  # Fastest available
            generation_config={
                'temperature': 0.7,  # Balanced for general conversation
                'top_p': 0.9,  # Higher for natural responses
                'max_output_tokens': 250  # Moderate length
            }
        )
        logger.info("Gemini AI initialized as fallback")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {str(e)}")
        print("⚠️ Check GEMINI_API_KEY and quota in Google Cloud Console")

# Custom Gemini Embedding Function for ChromaDB (matches TypeScript app)
class GeminiEmbeddingFunction:
    """Custom embedding function using Gemini API to match TypeScript implementation"""
    def __init__(self):
        self.name = "gemini-embedding-001"
        self.dimension = 768
        
    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings for documents using Gemini API"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY required for embeddings")
        
        embeddings = []
        for text in input:
            try:
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                # Return zero vector as fallback
                embeddings.append([0.0] * 768)  # Gemini embedding-001 is 768 dimensions
        
        return embeddings
    
    def embed_query(self, input: str) -> List[float]:
        """Generate embedding for a query using Gemini API"""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY required for embeddings")
        
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=input,
                task_type="retrieval_query"  # Use retrieval_query for search queries
            )
            # Return as numpy array for ChromaDB compatibility
            return np.array(result['embedding'])
        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}")
            # Return zero vector as fallback
            return np.array([0.0] * 768)

# Initialize ChromaDB with HTTP client
try:
    client = HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
    
    # Create custom embedding function
    embedding_function = GeminiEmbeddingFunction() if GEMINI_API_KEY else None
    
    # Get or create general knowledge collection
    try:
        # Try to get existing collection (don't specify embedding function for existing collections)
        collection = client.get_collection(name="knowledge_base")
        logger.info(f"Connected to knowledge_base collection with {collection.count()} documents")
        
        # Store embedding function separately for queries
        if embedding_function:
            collection._embedding_function = embedding_function
            
    except Exception as e:
        logger.warning(f"Collection not found, creating new one: {str(e)}")
        # Only specify embedding function when creating new collection
        if embedding_function:
            collection = client.create_collection(
                name="knowledge_base",
                metadata={"description": "General knowledge base for voice agent", "hnsw:space": "cosine"},
                embedding_function=embedding_function
            )
        else:
            collection = client.create_collection(
                name="knowledge_base",
                metadata={"description": "General knowledge base for voice agent"}
            )
        logger.info("Created new knowledge_base collection")
    
except Exception as e:
    logger.error(f"ChromaDB connection failed: {str(e)}")
    logger.error(f"Make sure ChromaDB server is running at {CHROMA_HOST}:{CHROMA_PORT}")
    collection = None

# Session storage
sessions = {}

def extract_number_from_speech(speech: str) -> Optional[float]:
    """Extract the first number from speech input using regex."""
    match = re.search(r'\b(\d+(?:\.\d+)?)\b', speech, re.IGNORECASE)
    return float(match.group(1)) if match else None

class GeneralAssistant:
    def __init__(self):
        self.gemini_requests_count = 0
        self.max_gemini_requests = 1000  # Daily limit
        self.rate_limit_reset = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
    def reset_daily_limits(self):
        """Reset daily API limits"""
        if datetime.now() >= self.rate_limit_reset:
            self.gemini_requests_count = 0
            self.rate_limit_reset = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            logger.info("Daily API limits reset")
        
    def get_user_profile(self, session_data: Dict) -> Dict:
        """Extract user profile from conversation"""
        profile = {
            "name": session_data.get("name", "unknown"),
            "preferences": session_data.get("preferences", []),
            "context": session_data.get("context", "general"),
            "location": session_data.get("location", "unknown"),
            "conversation_history": session_data.get("conversation_history", [])
        }
        return profile
    
    def determine_query_category(self, query: str) -> str:
        """Categorize user query to search appropriate information"""
        query_lower = query.lower()
        
        # Information seeking keywords
        info_keywords = [
            "what", "how", "why", "when", "where", "who", "explain", 
            "tell me", "information", "about", "define", "describe"
        ]
        
        # Action keywords
        action_keywords = [
            "help", "assist", "guide", "suggest", "recommend", 
            "advice", "find", "search", "show"
        ]
        
        # Conversational keywords
        conversational_keywords = [
            "hello", "hi", "hey", "thanks", "thank you", "goodbye", 
            "bye", "how are you", "what's up"
        ]
        
        if any(keyword in query_lower for keyword in conversational_keywords):
            return "conversational"
        elif any(keyword in query_lower for keyword in action_keywords):
            return "action_request"
        elif any(keyword in query_lower for keyword in info_keywords):
            return "information_seeking"
        else:
            return "general"
    
    def query_knowledge_base(self, query: str, n_results: int = 3) -> List[Dict]:
        """Query ChromaDB knowledge base with relevance filter"""
        if not collection:
            logger.warning("Knowledge base not available")
            return [{"content": "Knowledge base not available.", "metadata": {}}]
        
        try:
            # Check if collection has documents
            if collection.count() == 0:
                logger.warning("Knowledge base is empty")
                return [{"content": "Knowledge base is empty. Using AI knowledge.", "metadata": {}}]
            
            logger.info(f"🔍 Querying ChromaDB with: '{query[:100]}...'")
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            logger.info(f"📊 Raw ChromaDB results: Found {len(results['documents'][0])} documents")
            
            # Log all results with their distances
            for i, (doc, meta, dist) in enumerate(zip(
                results["documents"][0], 
                results["metadatas"][0], 
                results["distances"][0]
            ), 1):
                logger.info(f"  Result {i}: distance={dist:.4f}, preview='{doc[:100]}...'")
            
            # Filter results with high relevance (distance < 0.7 for general queries)
            filtered_results = [
                {"content": doc, "metadata": meta}
                for doc, meta, dist in zip(
                    results["documents"][0], 
                    results["metadatas"][0], 
                    results["distances"][0]
                )
                if dist < 0.7
            ]
            
            logger.info(f"✅ Filtered results: {len(filtered_results)} documents (threshold: 0.7)")
            
            return filtered_results if filtered_results else [
                {"content": "No highly relevant information found in knowledge base.", "metadata": {}}
            ]
        except Exception as e:
            logger.error(f"❌ Knowledge base query failed: {str(e)}")
            return [{"content": "Knowledge base query failed.", "metadata": {}}]
    
    def get_ai_response(self, prompt: str) -> Optional[str]:
        """Get AI response with Groq as primary (faster) and Gemini fallback"""
        self.reset_daily_limits()
        
        # Primary: Groq (faster inference)
        if groq_client:
            try:
                response = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=GROQ_MODEL,
                    temperature=0.7,  # Balanced for general conversation
                    max_tokens=250,  # Moderate length
                    top_p=0.9  # Natural responses
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Groq failed: {str(e)} - falling back to Gemini")
        
        # Fallback: Gemini (using synchronous version to avoid event loop issues)
        if gemini_model and self.gemini_requests_count < self.max_gemini_requests:
            try:
                self.gemini_requests_count += 1
                response = gemini_model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'max_output_tokens': 250
                    }
                )
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini failed: {str(e)}")
        
        # Ultimate fallback: Rule-based response
        return self.get_rule_based_response(prompt)
    
    def get_rule_based_response(self, query: str) -> str:
        """Simple rule-based fallback for when AI services are unavailable"""
        query_lower = query.lower()
        
        if any(greeting in query_lower for greeting in ["hello", "hi", "hey"]):
            return "Hello! I'm here to help you with any questions or tasks you have. What can I assist you with today?"
        elif any(farewell in query_lower for farewell in ["goodbye", "bye", "see you"]):
            return "Goodbye! Feel free to reach out anytime you need assistance. Have a great day!"
        elif "thank" in query_lower:
            return "You're welcome! Is there anything else I can help you with?"
        elif "help" in query_lower:
            return "I can assist you with various tasks, answer questions, provide information, and help with general queries. What would you like to know?"
        elif "what can you do" in query_lower or "capabilities" in query_lower:
            return "I can answer questions, provide information, help with tasks, and have conversations on various topics. Just let me know what you need!"
        else:
            return "I'm here to help! Could you please provide more details about what you'd like to know or do?"
    
    def generate_response(self, query: str, session_id: str) -> tuple[str, Optional[str]]:
        """Generate response with RAG and AI. Returns (response, follow_up_question)"""
        session = sessions.get(session_id, {})
        category = self.determine_query_category(query)
        
        # Get context from knowledge base (skip for conversational queries)
        if category != "conversational":
            rag_results = self.query_knowledge_base(query)
            context = "\n".join([result["content"] for result in rag_results]) if rag_results else "No relevant information found in knowledge base."
        else:
            context = "General conversation"
        
        profile = self.get_user_profile(session)
        
        # Build conversation history
        history = ""
        if profile["conversation_history"]:
            recent_history = profile["conversation_history"][-3:]  # Last 3 exchanges
            history = "\n".join([f"User: {h['user']}\nAssistant: {h['assistant']}" for h in recent_history])
        
        # Enhanced prompt for general assistant
        prompt = f"""
        You are a helpful, friendly, and knowledgeable voice assistant. Provide clear, concise, and accurate responses.
        Keep your responses conversational and natural, suitable for voice interaction. Limit responses to 100 words unless
        more detail is specifically requested.
        
        User Profile: {profile.get('name', 'User')}, Location: {profile['location']}, Context: {profile['context']}
        
        Recent Conversation:
        {history if history else 'No prior conversation'}
        
        Knowledge Base Context: {context}
        
        Current Query: {query}
        
        Respond in a natural, engaging tone suitable for voice conversation.
        """
        
        response = self.get_ai_response(prompt)
        
        # Update session with conversation history
        if "conversation_history" not in session:
            session["conversation_history"] = []
        
        session["conversation_history"].append({
            "user": query,
            "assistant": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 exchanges
        if len(session["conversation_history"]) > 10:
            session["conversation_history"] = session["conversation_history"][-10:]
        
        session["last_query"] = query
        session["last_response"] = response
        sessions[session_id] = session
        
        # No automatic follow-ups for general agent
        return response, None

assistant = GeneralAssistant()

@app.route("/voice", methods=["POST"])
def voice():
    """Handle incoming voice calls with general greeting"""
    session_id = request.form.get("CallSid")
    sessions[session_id] = {"conversation_history": []}
    
    response = VoiceResponse()
    response.say("Hello! I'm your voice assistant. How can I help you today?", 
                 voice="Polly.Aditi", language="en-IN")
    gather = Gather(input="speech", action="/process_speech", method="POST", 
                   speech_timeout="auto", language="en-IN", timeout=60)
    response.append(gather)
    return Response(str(response), mimetype="text/xml")

@app.route("/process_speech", methods=["POST"])
def process_speech():
    """Process user speech and respond"""
    speech = request.form.get("SpeechResult", "").strip()
    session_id = request.form.get("CallSid")
    session = sessions.get(session_id, {"conversation_history": []})
    
    response = VoiceResponse()
    
    if not speech:
        response.say("I didn't catch that. Please try again.", 
                    voice="Polly.Aditi", language="en-IN")
        gather = Gather(input="speech", action="/process_speech", method="POST", 
                       speech_timeout="auto", language="en-IN", timeout=60)
        response.append(gather)
        return Response(str(response), mimetype="text/xml")
    
    # Check for conversation end
    if any(end_phrase in speech.lower() for end_phrase in ["goodbye", "end call", "bye", "that's all"]):
        response.say("Thank you for using the voice assistant. Have a great day! Goodbye.", 
                    voice="Polly.Aditi", language="en-IN")
        response.hangup()
        return Response(str(response), mimetype="text/xml")
    
    # Generate response
    ai_response, follow_up = assistant.generate_response(speech, session_id)
    
    response.say(ai_response, voice="Polly.Aditi", language="en-IN")
    
    # Continue conversation
    gather = Gather(input="speech", action="/process_speech", method="POST", 
                   speech_timeout="auto", language="en-IN", timeout=60)
    response.append(gather)
    
    sessions[session_id] = session
    
    return Response(str(response), mimetype="text/xml")

@app.route("/test", methods=["GET"])
def test_interface():
    """Test interface"""
    collection_info = "not available"
    if collection:
        try:
            collection_info = f"available with {collection.count()} documents"
        except:
            collection_info = "available (count unavailable)"
    
    return f"""
    <html>
        <head><title>General Voice Assistant Test</title></head>
        <body>
            <h1>General Voice Assistant Test Interface</h1>
            <p>System is running. Use Twilio to test voice calls.</p>
            <p>Knowledge Base: {collection_info}</p>
            <p>ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}</p>
        </body>
    </html>
    """

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    status = "healthy" if (groq_client or gemini_model) else "degraded"
    kb_status = "available" if collection else "unavailable"
    
    try:
        kb_count = collection.count() if collection else 0
    except:
        kb_count = 0
    
    return jsonify({
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "ai_service": "groq" if groq_client else "gemini" if gemini_model else "none",
        "knowledge_base": kb_status,
        "kb_documents": kb_count,
        "chroma_server": f"{CHROMA_HOST}:{CHROMA_PORT}"
    })

# Add error handler for uncaught exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(e)}")
    
    # For Twilio webhooks, always return valid TwiML
    if request.endpoint in ['voice', 'process_speech']:
        response = VoiceResponse()
        response.say("I encountered a technical issue. Please try again.", 
                    voice="Polly.Aditi", language="en-IN")
        return Response(str(response), mimetype="text/xml")
    
    # For API endpoints
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again or contact support"
    }), 500

def verify_system_health():
    """Verify system components with fallbacks"""
    issues = []
    
    # Check ChromaDB
    try:
        if not collection:
            issues.append(f"ChromaDB not connected at {CHROMA_HOST}:{CHROMA_PORT}")
        else:
            try:
                count = collection.count()
                if count == 0:
                    issues.append("Knowledge base is empty - responses will use AI knowledge only")
            except Exception as e:
                issues.append(f"ChromaDB connection error: {e}")
    except Exception as e:
        issues.append(f"ChromaDB error: {e}")
    
    # Check AI services
    ai_available = bool(groq_client or gemini_model)
    if not ai_available:
        issues.append("No AI services available - will use rule-based responses")
    
    # Check Twilio config
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN):
        issues.append("Twilio not configured - voice calls won't work")
    
    if issues:
        print("⚠️  System Issues Found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n✅ System will continue with available fallbacks")
    else:
        print("✅ All systems operational")
    
    return len(issues) == 0

if __name__ == "__main__":
    # System health check
    print("🤖 General Voice Assistant Starting...")
    print("=" * 50)
    
    all_systems_ok = verify_system_health()
    
    if not all_systems_ok:
        print("\n⚠️  Running in degraded mode with fallbacks")
        print("Some features may be limited but voice calls will work")
    
    print("\nServices Available:")
    print(f"✓ Voice Interface (Twilio): {'Yes' if TWILIO_ACCOUNT_SID else 'No'}")
    print(f"✓ AI Services: {'Yes' if (groq_client or gemini_model) else 'Rule-based only'}")
    print(f"✓ ChromaDB Server: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"✓ Knowledge Base: {'Yes' if collection else 'No'}")
    print(f"✓ Fallback Responses: Always available")
    
    print("=" * 50)
    print(f"🌐 Test Interface: http://localhost:5000/test")
    print(f"📊 Health Check: http://localhost:5000/health") 
    print(f"☎️  Twilio Webhook: Use HTTPS ngrok URL + /voice")
    print("=" * 50)
    
    try:
        app.run(debug=False, port=5000, host='0.0.0.0', threaded=True)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("Check if port 5000 is available or try a different port")