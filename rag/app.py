# Add this import at the top of the file
from dotenv import load_dotenv

# Load environment variables from .env file
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
from chromadb import HttpClient
import time
import requests

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

# Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# Initialize ChromaDB
client = HttpClient(host="localhost", port=8000)
# embedding_function = embedding_functions.DefaultEmbeddingFunction()
collection = client.get_collection(name="frcrce_knowledge")
embedding_function = embedding_functions.DefaultEmbeddingFunction()


# Try to get the collection created by the knowledge base setup
try:
    collection = client.get_collection(
        name="frcrce_knowledge",
        embedding_function=embedding_function
    )
    logger.info("Successfully connected to FR CRCE knowledge base")
except Exception as e:
    logger.error(f"Could not connect to knowledge base: {e}")
    logger.error("Make sure you've run the knowledge base setup script first")
    collection = None

# Session storage for tracking conversation state
sessions = {}

def get_or_create_session(call_sid):
    """Create or retrieve a session for the current call"""
    if call_sid not in sessions:
        sessions[call_sid] = {
            "conversation_history": [
                {"role": "system", "content": "You are a helpful admission counselor for FR CRCE college. Be friendly, informative, and concise. Your goal is to help prospective students and parents get accurate information about the college. Keep responses short and focused for voice calls. Always provide specific, helpful information based on the knowledge base."}
            ],
            "user_info": {
                "query_type": None,
                "interest_area": None,
                "location_mentioned": False,
                "contact_info_needed": False
            },
            "current_step": "initial"
        }
    return sessions[call_sid]

def query_rag(query, session):
    """Query the RAG system to generate a response"""
    if not collection:
        return "I'm sorry, the knowledge base is not available right now. Please try again later or contact the college directly at their official website."
    
    try:
        # First, retrieve relevant information from ChromaDB
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        
        # Extract retrieved documents
        retrieved_docs = results['documents'][0] if results['documents'] and results['documents'][0] else []
        retrieved_metadatas = results['metadatas'][0] if results['metadatas'] and results['metadatas'][0] else []
        
        if not retrieved_docs:
            return "I didn't find specific information about that. Could you please ask about admission process, fees, courses, placements, or facilities at FR CRCE?"
        
        # Format retrieved context
        context = "\n\n".join([
            f"Category: {meta.get('category', 'General')}\n{doc}" 
            for doc, meta in zip(retrieved_docs, retrieved_metadatas)
        ])
        
        # Update conversation with user input
        session["conversation_history"].append({"role": "user", "content": query})
        
        # Create prompt for the LLM
        prompt = f"""Based on the following FR CRCE college information:

{context}

User's question: {query}

Conversation history:
{json.dumps(session["conversation_history"][-3:], indent=2)}

Respond as a helpful FR CRCE admission counselor. Keep responses under 4 sentences for voice calls. 
Be specific and accurate based only on the provided information.
If you need more details from the user, ask one clear question.
If the information isn't in the knowledge base, direct them to visit the college or check the official website.
"""

        # Call Groq API with proper error handling
        if not GROQ_API_KEY:
            logger.error("GROQ_API_KEY is not set")
            return "I'm having trouble accessing information right now. Please contact FR CRCE directly for the most current information."
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 300
            },
            timeout=30
        )
        
        # Check if request was successful
        if response.status_code != 200:
            logger.error(f"Groq API error - Status: {response.status_code}, Response: {response.text}")
            return "I'm having trouble processing your request right now. Please contact FR CRCE directly for information."
        
        response_data = response.json()
        
        # Check if response has expected structure
        if "choices" not in response_data or not response_data["choices"]:
            logger.error(f"Unexpected API response structure: {response_data}")
            return "I'm having trouble processing your request right now. Please contact FR CRCE directly for information."
        
        agent_response = response_data["choices"][0]["message"]["content"]
        
        # Update conversation history
        session["conversation_history"].append({"role": "assistant", "content": agent_response})
        
        return agent_response
        
    except requests.exceptions.Timeout:
        logger.error("Groq API request timed out")
        return "I'm having trouble processing your request right now. Please contact FR CRCE directly for information."
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error calling Groq API: {str(e)}")
        return "I'm having trouble processing your request right now. Please contact FR CRCE directly for information."
    except Exception as e:
        logger.error(f"Unexpected error in query_rag: {str(e)}")
        return "I'm having trouble processing your request right now. Please contact FR CRCE directly for information."

@app.route("/voice", methods=["POST"])
def voice():
    """Handle incoming calls and start the conversation using Twilio's Say TTS"""
    response = VoiceResponse()
    call_sid = request.values.get("CallSid")
    session = get_or_create_session(call_sid)
    
    # Initial greeting using Twilio's Say
    response.say("Hello! Welcome to FR CRCE college information service. I can help you with admission details, fees, courses, placements, and facilities. What would you like to know?", 
                 voice="woman", language="en-IN")
    
    # Gather speech input
    gather = Gather(
        input="speech",
        action="/process_speech",
        method="POST",
        speechTimeout="3",
        speechModel="phone_call",
        language="en-IN"
    )
    response.append(gather)
    
    # If no speech detected, retry
    response.redirect("/voice")
    
    return Response(str(response), mimetype="text/xml")

@app.route("/process_speech", methods=["POST"])
def process_speech():
    """Process speech input from the caller using Twilio's Say TTS"""
    logger.debug("===== PROCESS SPEECH =====")
    logger.debug(f"All request values: {request.values.to_dict()}")

    response = VoiceResponse()
    call_sid = request.values.get("CallSid")
    logger.debug(f"Call SID: {call_sid}")

    session = get_or_create_session(call_sid)
    session["call_sid"] = call_sid

    logger.debug(f"Current session state: {json.dumps(session, indent=2)}")

    # Get speech input
    speech_result = request.values.get("SpeechResult")
    logger.debug(f"Speech result: {speech_result}")

    if speech_result:
        # Query RAG for response
        agent_response = query_rag(speech_result, session)
        
        # Use Twilio's Say for the response
        response.say(agent_response, voice="woman", language="en-IN")
        
        # Send conversation to dashboard (optional)
        send_to_dashboard(session)
        
        # Check if this seems like a goodbye or the user is satisfied
        if any(word in speech_result.lower() for word in ["thank you", "thanks", "bye", "goodbye", "that's all", "sufficient"]):
            response.say("Thank you for contacting FR CRCE. For more information, visit our website at www.frcrce.ac.in or visit our campus at Bandra West, Mumbai. Have a great day!", voice="woman", language="en-IN")
            response.hangup()
            return Response(str(response), mimetype="text/xml")
        
        # Gather more speech input
        gather = Gather(
            input="speech",
            action="/process_speech",
            method="POST",
            speechTimeout="3",
            speechModel="phone_call",
            language="en-IN"
        )
        response.append(gather)
        
        # Add a helpful prompt for continued conversation
        response.say("Is there anything else you'd like to know about FR CRCE?", voice="woman", language="en-IN")
        
    else:
        # Handle case when speech cannot be recognized
        response.say("I couldn't understand that clearly. Could you please repeat your question about FR CRCE college?", voice="woman", language="en-IN")
        gather = Gather(
            input="speech",
            action="/process_speech",
            method="POST",
            speechTimeout="3",
            speechModel="phone_call",
            language="en-IN"
        )
        response.append(gather)
    
    # If no further input received, provide helpful closure
    response.say("For more information, you can visit FR CRCE website at www.frcrce.ac.in or call the college directly. Thank you!", voice="woman", language="en-IN")
    
    return Response(str(response), mimetype="text/xml")

def send_to_dashboard(session):
    """Send conversation information to the dashboard via websocket server"""
    try:
        # Prepare data for the dashboard
        conversation_data = session["conversation_history"]
        user_info = session["user_info"]
            
        payload = {
            "id": session.get("call_sid", f"call-{int(time.time())}"),
            "convo": {
                "data": conversation_data
            },
            "user_info": user_info
        }
            
        # Send POST request to the websocket server (if you have one)
        response = requests.post(
            "http://localhost:8080/twilio-webhook",  # Update this URL to your websocket server
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
            
        if response.status_code == 200:
            logger.info("Successfully sent data to dashboard")
        else:
            logger.error(f"Failed to send data to dashboard: {response.status_code}")
                
    except Exception as e:
        logger.debug(f"Dashboard not available (this is optional): {str(e)}")

# Optional endpoint for direct testing without Twilio
@app.route("/test", methods=["GET", "POST"])
def test_endpoint():
    """Test endpoint to simulate conversation without Twilio"""
    if request.method == "POST":
        user_input = request.form.get("user_input") or request.json.get("user_input")
        test_session = get_or_create_session("test_session")
        response = query_rag(user_input, test_session)
        return {
            "response": response,
            "user_info": test_session["user_info"],
            "session_id": "test_session"
        }
    return """
    <html>
        <head><title>FR CRCE Information System Test</title></head>
        <body>
            <h1>Test FR CRCE Information System</h1>
            <form method="post">
                <input type="text" name="user_input" placeholder="Ask about FR CRCE..." style="width: 300px;">
                <button type="submit">Ask</button>
            </form>
            <p><strong>Try asking about:</strong></p>
            <ul>
                <li>What is the fee structure?</li>
                <li>How are the placements?</li>
                <li>What courses are offered?</li>
                <li>Where is the college located?</li>
                <li>What about hostel facilities?</li>
            </ul>
        </body>
    </html>
    """

@app.route("/test_webhook", methods=["GET", "POST"])
def test_webhook():
    """Simple test endpoint to verify the server is responsive"""
    request_data = {
        "method": request.method,
        "url": request.url,
        "headers": dict(request.headers),
        "form_data": request.form.to_dict() if request.form else {},
        "query_params": request.args.to_dict() if request.args else {}
    }
    
    return jsonify({
        "status": "success",
        "message": "FR CRCE information system webhook is working",
        "timestamp": time.time(),
        "request_data": request_data
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
        }
    }
    
    if collection:
        try:
            # Test ChromaDB connection
            test_result = collection.query(query_texts=["test"], n_results=1)
            health_status["services"]["chromadb_query"] = True
        except:
            health_status["services"]["chromadb_query"] = False
    
    return jsonify(health_status)

if __name__ == "__main__":
    # Check if knowledge base is available
    if not collection:
        print("WARNING: Knowledge base not found!")
        print("Please run the knowledge base setup script first:")
        print("python setup_knowledge_base.py")
        print()
    
    # Tell Flask we're behind a proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
        
    print(f"Starting FR CRCE Information System on port 5000")
    print("Make sure to use the HTTPS URL from ngrok for your Twilio webhook")
    print("Test the system at: http://localhost:5000/test")
    app.run(debug=True, port=5000)