# Add this import at the top of the file
from dotenv import load_dotenv

# Load environment variables from .env file FIRST - before other imports
load_dotenv()

# The rest of your imports
from flask import Flask, request, Response, jsonify, redirect
import os
import json
import chromadb
import requests
import logging
from twilio.twiml.voice_response import VoiceResponse, Gather
from chromadb.utils import embedding_functions
import time

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.before_request
def before_request():
    # Force HTTPS for all routes when using ngrok
    if 'ngrok' in request.host and request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# Configuration - Updated to check for required keys
def check_environment():
    """Check if all required environment variables are set"""
    required_keys = {
        'GROQ_API_KEY': 'Get from https://console.groq.com/',
        'TWILIO_ACCOUNT_SID': 'Get from https://console.twilio.com/',
        'TWILIO_AUTH_TOKEN': 'Get from https://console.twilio.com/'
    }
    
    missing_keys = []
    for key, source in required_keys.items():
        if not os.environ.get(key):
            missing_keys.append(f"{key} ({source})")
    
    if missing_keys:
        logger.error("Missing required environment variables:")
        for key in missing_keys:
            logger.error(f"  - {key}")
        return False
    return True

# Check environment variables
if not check_environment():
    print("\n" + "="*60)
    print("ERROR: Missing required API keys!")
    print("="*60)
    print("Please add the following to your .env file:")
    print("- GROQ_API_KEY (from https://console.groq.com/)")
    print("- TWILIO_ACCOUNT_SID (from https://console.twilio.com/)")
    print("- TWILIO_AUTH_TOKEN (from https://console.twilio.com/)")
    print("\nSee the provided .env file template for details.")
    print("="*60)
    exit(1)

# Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "./chroma_db")

# Initialize ChromaDB
try:
    client = chromadb.PersistentClient(CHROMA_DB_PATH)
    embedding_function = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_collection(
        name="frcrce_knowledge",
        embedding_function=embedding_function
    )
    logger.info("Successfully connected to FR CRCE knowledge base")
    logger.info(f"Knowledge base contains {collection.count()} documents")
except Exception as e:
    logger.error(f"Could not connect to knowledge base: {e}")
    logger.error("Make sure you've run: python frcrce_knowledge_setup.py")
    collection = None

# Session storage for tracking conversation state
sessions = {}

def get_or_create_session(call_sid):
    """Create or retrieve a session for the current call"""
    if call_sid not in sessions:
        sessions[call_sid] = {
            "conversation_history": [
                {
                    "role": "system", 
                    "content": "You are a helpful admission counselor for FR CRCE college in Mumbai. Be friendly, informative, and concise. Your goal is to help prospective students and parents get accurate information about the college. Keep responses under 3 sentences for voice calls. Always provide specific, helpful information based on the knowledge base."
                }
            ],
            "user_info": {
                "query_type": None,
                "interest_area": None,
                "location_mentioned": False,
                "contact_info_needed": False
            },
            "current_step": "initial",
            "start_time": time.time()
        }
    return sessions[call_sid]

def query_rag(query, session):
    """Query the RAG system to generate a response"""
    if not collection:
        return "I'm sorry, the knowledge base is not available right now. Please contact FR CRCE directly at www.frcrce.ac.in or visit the campus at Bandra West, Mumbai."
    
    try:
        logger.info(f"Processing query: {query}")
        
        # Retrieve relevant information from ChromaDB
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        
        # Extract retrieved documents
        retrieved_docs = results['documents'][0] if results['documents'] and results['documents'][0] else []
        retrieved_metadatas = results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else []
        
        logger.info(f"Retrieved {len(retrieved_docs)} relevant documents")
        
        if not retrieved_docs:
            return "I didn't find specific information about that. You can ask me about admission process, fees, courses, placements, facilities, or location of FR CRCE."
        
        # Format retrieved context with priorities
        context_parts = []
        for doc, meta in zip(retrieved_docs, retrieved_metadatas):
            priority = meta.get('priority', 'medium')
            category = meta.get('category', 'general')
            context_parts.append(f"[{priority.upper()} PRIORITY - {category}]\n{doc}")
        
        context = "\n\n".join(context_parts)
        
        # Update conversation with user input
        session["conversation_history"].append({"role": "user", "content": query})
        
        # Create optimized prompt for voice responses
        prompt = f"""Based on the following FR CRCE college information, provide a helpful response:

{context}

User's question: {query}

IMPORTANT INSTRUCTIONS:
- Keep response under 3 sentences for voice call
- Be specific and accurate using only the provided information
- If information is not available, direct them to visit college or website
- Sound friendly and helpful like an admission counselor
- Focus on the most relevant information first

Response:"""

        # Call Groq API with improved error handling
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 250,
                "top_p": 0.9
            },
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Groq API error - Status: {response.status_code}")
            return "I'm having trouble right now. For immediate help, please contact FR CRCE at their official website www.frcrce.ac.in or visit the campus."
        
        response_data = response.json()
        
        if "choices" not in response_data or not response_data["choices"]:
            logger.error(f"Unexpected API response structure")
            return "I'm having trouble processing that. Please contact FR CRCE directly for accurate information."
        
        agent_response = response_data["choices"][0]["message"]["content"].strip()
        
        # Update conversation history
        session["conversation_history"].append({"role": "assistant", "content": agent_response})
        
        logger.info(f"Generated response: {agent_response[:100]}...")
        return agent_response
        
    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return "I'm processing slowly right now. For quick answers, visit FR CRCE website at www.frcrce.ac.in."
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        return "I'm having technical difficulties. Please contact FR CRCE directly for information."
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return "I'm having trouble right now. Please visit FR CRCE at Bandra West, Mumbai or check www.frcrce.ac.in."

@app.route("/voice", methods=["POST"])
def voice():
    """Handle incoming calls and start the conversation"""
    response = VoiceResponse()
    call_sid = request.values.get("CallSid")
    from_number = request.values.get("From")
    
    logger.info(f"Incoming call from {from_number}, Call SID: {call_sid}")
    
    session = get_or_create_session(call_sid)
    
    # Welcome message optimized for Indian context
    welcome_message = ("Hello! Welcome to F R C R C E college information service. "
                      "I can help you with admission details, fees, courses, placements, and facilities. "
                      "What would you like to know?")
    
    response.say(welcome_message, voice="woman", language="en-IN")
    
    # Gather speech input with optimized settings
    gather = Gather(
        input="speech",
        action="/process_speech",
        method="POST",
        speechTimeout="4",
        speechModel="phone_call",
        language="en-IN",
        enhanced="true"
    )
    response.append(gather)
    
    # Fallback message
    response.say("I didn't hear anything. Please call back if you need information about F R C R C E college.", 
                voice="woman", language="en-IN")
    
    return Response(str(response), mimetype="text/xml")

@app.route("/process_speech", methods=["POST"])
def process_speech():
    """Process speech input from the caller"""
    logger.debug("Processing speech input")
    
    response = VoiceResponse()
    call_sid = request.values.get("CallSid")
    speech_result = request.values.get("SpeechResult")
    confidence = request.values.get("Confidence", "0")
    
    logger.info(f"Speech: '{speech_result}' (Confidence: {confidence})")
    
    session = get_or_create_session(call_sid)
    session["call_sid"] = call_sid
    
    if speech_result:
        # Check for conversation ending phrases
        ending_phrases = ["thank you", "thanks", "bye", "goodbye", "that's all", 
                         "sufficient", "enough", "ok bye", "okay bye"]
        
        if any(phrase in speech_result.lower() for phrase in ending_phrases):
            response.say("Thank you for contacting F R C R C E. For more information, "
                        "visit our website at www dot f r c r c e dot ac dot in "
                        "or visit our campus at Bandra West, Mumbai. Have a great day!",
                        voice="woman", language="en-IN")
            response.hangup()
            
            # Send to dashboard before ending
            send_to_dashboard(session)
            return Response(str(response), mimetype="text/xml")
        
        # Query RAG system
        agent_response = query_rag(speech_result, session)
        
        # Speak the response
        response.say(agent_response, voice="woman", language="en-IN")
        
        # Gather more input
        gather = Gather(
            input="speech",
            action="/process_speech",
            method="POST",
            speechTimeout="4",
            speechModel="phone_call",
            language="en-IN",
            enhanced="true"
        )
        response.append(gather)
        
        # Prompt for more questions
        response.say("Is there anything else you'd like to know about F R C R C E?", 
                    voice="woman", language="en-IN")
        
    else:
        # Handle unclear speech
        response.say("I couldn't understand that clearly. Could you please repeat your question about F R C R C E college?", 
                    voice="woman", language="en-IN")
        gather = Gather(
            input="speech",
            action="/process_speech", 
            method="POST",
            speechTimeout="4",
            speechModel="phone_call",
            language="en-IN",
            enhanced="true"
        )
        response.append(gather)
    
    # Final fallback
    response.say("For more information, visit www dot f r c r c e dot ac dot in. Thank you!", 
                voice="woman", language="en-IN")
    
    # Send conversation to dashboard
    send_to_dashboard(session)
    
    return Response(str(response), mimetype="text/xml")

def send_to_dashboard(session):
    """Send conversation information to the dashboard"""
    try:
        websocket_port = os.environ.get("WEBSOCKET_PORT", "8080")
        payload = {
            "id": session.get("call_sid", f"call-{int(time.time())}"),
            "convo": {
                "data": session["conversation_history"]
            },
            "user_info": session["user_info"]
        }
        
        response = requests.post(
            f"http://localhost:{websocket_port}/twilio-webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=3
        )
        
        if response.status_code == 200:
            logger.info("Successfully sent data to dashboard")
        else:
            logger.debug(f"Dashboard response: {response.status_code}")
            
    except Exception as e:
        logger.debug(f"Dashboard not available (optional): {str(e)}")

# Testing and health endpoints
@app.route("/test", methods=["GET", "POST"])
def test_endpoint():
    """Test endpoint for direct testing"""
    if request.method == "POST":
        user_input = request.form.get("user_input") or request.json.get("user_input")
        if not user_input:
            return {"error": "No input provided"}, 400
            
        test_session = get_or_create_session("test_session")
        response = query_rag(user_input, test_session)
        
        return {
            "response": response,
            "user_info": test_session["user_info"],
            "session_id": "test_session",
            "conversation_length": len(test_session["conversation_history"])
        }
        
    return """
    <html>
        <head><title>FR CRCE Information System Test</title></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto;">
            <h1>Test FR CRCE Information System</h1>
            <form method="post">
                <input type="text" name="user_input" placeholder="Ask about FR CRCE..." 
                       style="width: 400px; padding: 10px; font-size: 16px;">
                <button type="submit" style="padding: 10px 20px; font-size: 16px;">Ask</button>
            </form>
            <h3>Try asking about:</h3>
            <ul>
                <li>What is the fee structure?</li>
                <li>How are the placements?</li>
                <li>What courses are offered?</li>
                <li>Where is the college located?</li>
                <li>What about hostel facilities?</li>
                <li>Tell me about scholarships</li>
                <li>How to apply for admission?</li>
            </ul>
        </body>
    </html>
    """

@app.route("/test_webhook", methods=["GET", "POST"])
def test_webhook():
    """Test webhook endpoint"""
    return jsonify({
        "status": "success",
        "message": "FR CRCE webhook is working",
        "timestamp": time.time(),
        "method": request.method
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "chromadb": collection is not None,
            "groq_api": GROQ_API_KEY is not None,
            "twilio": TWILIO_ACCOUNT_SID is not None and TWILIO_AUTH_TOKEN is not None
        },
        "active_sessions": len(sessions),
        "knowledge_base_docs": collection.count() if collection else 0
    }
    
    # Test services
    if collection:
        try:
            collection.query(query_texts=["test"], n_results=1)
            health_status["services"]["chromadb_query"] = True
        except:
            health_status["services"]["chromadb_query"] = False
    
    return jsonify(health_status)

if __name__ == "__main__":
    # Final checks before starting
    if not collection:
        print("WARNING: Knowledge base not found!")
        print("Please run: python frcrce_knowledge_setup.py")
        print()
    else:
        print(f"Knowledge base loaded with {collection.count()} documents")
    
    # Configure Flask for production
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
    
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting FR CRCE Information System on port {port}")
    print(f"Test the system at: http://localhost:{port}/test")
    print("Make sure to use HTTPS URL from ngrok for Twilio webhook")
    print("="*60)
    
    app.run(debug=True, port=port, host='0.0.0.0')