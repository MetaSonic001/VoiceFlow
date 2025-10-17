# twilio_setup.py - General Voice Assistant Setup

import os
import sys
from twilio.rest import Client
import subprocess
import time
import requests
from dotenv import load_dotenv
import json
import platform

# Load environment variables
load_dotenv()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]
    optional_vars = ["GEMINI_API_KEY", "GROQ_API_KEY"]
    
    missing = []
    warnings = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    for var in optional_vars:
        if not os.environ.get(var):
            warnings.append(var)
    
    if missing:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
        print("\n📝 Please add them to your .env file:")
        for var in missing:
            print(f"{var}=your_{var.lower()}_from_twilio_console")
        return False
    
    if len(warnings) == 2:
        print("⚠️  Warning: No AI service API keys found (GEMINI_API_KEY, GROQ_API_KEY)")
        print("At least one is required for the assistant to function properly.")
        return False
    elif warnings:
        print(f"ℹ️  Info: {warnings[0]} not set, will use available AI service")
    
    return True

def check_chromadb_connection():
    """Check if ChromaDB server is accessible"""
    chroma_host = os.environ.get("CHROMA_HOST", "localhost")
    chroma_port = os.environ.get("CHROMA_PORT", "8000")
    
    try:
        response = requests.get(f"http://{chroma_host}:{chroma_port}/api/v2/heartbeat", timeout=5)
        if response.status_code == 200:
            print(f"✅ ChromaDB server is running at {chroma_host}:{chroma_port}")
            
            # Try to get collection info
            try:
                collections_response = requests.get(
                    f"http://{chroma_host}:{chroma_port}/api/v2/collections",
                    timeout=5
                )
                if collections_response.status_code == 200:
                    collections = collections_response.json()
                    if collections:
                        print(f"   📚 Found {len(collections)} collection(s)")
                    else:
                        print("   ℹ️  No collections found (will create on first use)")
            except:
                pass
            
            return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Cannot connect to ChromaDB server at {chroma_host}:{chroma_port}")
        print("\n📝 Please start ChromaDB server:")
        print("   Option 1: chroma run --host localhost --port 8000")
        print("   Option 2: docker run -p 8000:8000 chromadb/chroma")
        return False
    except Exception as e:
        print(f"❌ Error checking ChromaDB: {str(e)}")
        return False

def start_cloudflared(port=5000):
    """Start cloudflared tunnel for Twilio webhooks"""
    print(f"🚀 Starting cloudflared tunnel on port {port}...")
    
    # Check if cloudflared is installed
    try:
        result = subprocess.run(["cloudflared", "--version"], 
                              check=True, capture_output=True, text=True)
        print(f"✅ Cloudflared version: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: cloudflared is not installed or not in PATH.")
        print("\n📥 Please install cloudflared:")
        print("   Windows: Download from https://github.com/cloudflare/cloudflared/releases")
        print("   macOS: brew install cloudflared")
        print("   Linux: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64")
        print("           sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared")
        print("           sudo chmod +x /usr/local/bin/cloudflared")
        print("\n✨ No authentication required!")
        return None
    
    # Kill existing cloudflared processes
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "cloudflared.exe"], 
                          capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)
        time.sleep(1)
    except:
        pass
    
    # Start cloudflared process with output capture
    print("⏳ Starting cloudflared tunnel...")
    process = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Wait for cloudflared to start and capture URL
    print("⏳ Waiting for tunnel to establish...")
    tunnel_url = None
    start_time = time.time()
    
    try:
        while time.time() - start_time < 30:  # 30 second timeout
            line = process.stdout.readline()
            if line:
                print(f"   {line.strip()}")
                # Look for the tunnel URL in output
                if "trycloudflare.com" in line or "https://" in line:
                    # Extract URL from line
                    import re
                    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                    if match:
                        tunnel_url = match.group(0)
                        print(f"\n✅ Cloudflared tunnel established: {tunnel_url}")
                        return tunnel_url
            time.sleep(0.1)
        
        # If we didn't find URL in output, try alternative parsing
        if not tunnel_url:
            print("⚠️  Could not detect tunnel URL automatically")
            print("Please check cloudflared output above for the tunnel URL")
            manual_url = input("\nEnter the cloudflared URL (or press Enter to retry): ").strip()
            if manual_url:
                return manual_url
            return None
            
    except Exception as e:
        print(f"❌ Error starting cloudflared: {str(e)}")
        return None

def test_flask_app(tunnel_url):
    """Test if Flask app is responding"""
    try:
        print("🧪 Testing Flask application...")
        
        # Test health endpoint
        try:
            response = requests.get(f"{tunnel_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Health check: OK")
                print(f"      - Status: {data.get('status')}")
                print(f"      - AI Service: {data.get('ai_service')}")
                print(f"      - Knowledge Base: {data.get('knowledge_base')}")
                print(f"      - KB Documents: {data.get('kb_documents', 0)}")
            else:
                print(f"   ⚠️  Health check: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Health check: {str(e)}")
        
        # Test main interface
        try:
            response = requests.get(f"{tunnel_url}/test", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Test interface: OK")
            else:
                print(f"   ⚠️  Test interface: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Test interface: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Flask app test failed: {str(e)}")
        print("Make sure to start Flask app with: python app.py")
        return False

def setup_twilio_phone(tunnel_url):
    """Configure Twilio phone number for voice assistant"""
    if not check_environment():
        return None
    
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    
    try:
        client = Client(account_sid, auth_token)
        account = client.api.accounts(account_sid).fetch()
        print(f"✅ Connected to Twilio account: {account.friendly_name}")
        
    except Exception as e:
        print(f"❌ Error connecting to Twilio: {str(e)}")
        print("Please check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        return None
    
    # Get available phone numbers
    try:
        numbers = client.incoming_phone_numbers.list()
        
        if not numbers:
            print("\n📞 No phone numbers found in your Twilio account.")
            print("You need to purchase a phone number for the voice service.")
            
            # Search for available numbers
            countries = [
                {"code": "IN", "name": "India", "type": "local"},
                {"code": "US", "name": "United States", "type": "toll_free"},
                {"code": "GB", "name": "United Kingdom", "type": "local"},
                {"code": "CA", "name": "Canada", "type": "local"}
            ]
            
            print("\n🌍 Available countries for phone numbers:")
            for i, country in enumerate(countries, 1):
                print(f"{i}. {country['name']} ({country['code']}) - {country['type']}")
            
            while True:
                try:
                    choice = input(f"\nSelect country (1-{len(countries)}) or 'skip': ").strip()
                    if choice.lower() == 'skip':
                        print("⏭️  Skipping phone number purchase. You can configure manually later.")
                        return None
                    
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(countries):
                        selected_country = countries[choice_idx]
                        break
                    else:
                        print("❌ Invalid choice. Please try again.")
                except ValueError:
                    print("❌ Please enter a number.")
            
            # Search for available numbers
            try:
                print(f"\n🔍 Searching for numbers in {selected_country['name']}...")
                
                if selected_country['type'] == 'toll_free':
                    available_numbers = client.available_phone_numbers(selected_country['code']).toll_free.list(limit=10)
                else:
                    available_numbers = client.available_phone_numbers(selected_country['code']).local.list(limit=10)
                
                if not available_numbers:
                    print(f"❌ No numbers available in {selected_country['name']}.")
                    print("Try a different country or check your Twilio account balance.")
                    return None
                
                print(f"\n📱 Available phone numbers:")
                for i, number in enumerate(available_numbers[:5], 1):
                    print(f"{i}. {number.phone_number} - {number.friendly_name}")
                
                while True:
                    try:
                        selection = input(f"\nSelect number (1-{min(5, len(available_numbers))}): ").strip()
                        selection_idx = int(selection) - 1
                        if 0 <= selection_idx < len(available_numbers):
                            selected_number = available_numbers[selection_idx]
                            break
                        else:
                            print("❌ Invalid selection.")
                    except ValueError:
                        print("❌ Please enter a number.")
                
                # Purchase the number
                print(f"\n💳 Purchasing {selected_number.phone_number}...")
                webhook_url = f"{tunnel_url}/voice"
                
                purchased_number = client.incoming_phone_numbers.create(
                    phone_number=selected_number.phone_number,
                    voice_url=webhook_url,
                    voice_method="POST"
                )
                
                print(f"✅ Successfully purchased and configured: {purchased_number.phone_number}")
                return purchased_number.phone_number
                        
            except Exception as e:
                print(f"❌ Error searching/purchasing numbers: {str(e)}")
                if "does not appear to be a valid country code" in str(e):
                    print("Please use a valid country code.")
                elif "insufficient funds" in str(e).lower():
                    print("Please add funds to your Twilio account.")
                return None
        
        else:
            # Use existing numbers
            print(f"\n📱 Found {len(numbers)} phone number(s) in your account:")
            for i, number in enumerate(numbers, 1):
                print(f"{i}. {number.phone_number} ({number.friendly_name})")
            
            if len(numbers) == 1:
                choice = input(f"\nConfigure {numbers[0].phone_number} for voice service? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    selected_number = numbers[0]
                else:
                    print("⏭️  Setup cancelled.")
                    return None
            else:
                while True:
                    try:
                        selection = input(f"\nSelect number to configure (1-{len(numbers)}): ").strip()
                        selection_idx = int(selection) - 1
                        if 0 <= selection_idx < len(numbers):
                            selected_number = numbers[selection_idx]
                            break
                        else:
                            print("❌ Invalid selection.")
                    except ValueError:
                        print("❌ Please enter a number.")
            
            # Configure the selected number
            try:
                webhook_url = f"{tunnel_url}/voice"
                selected_number.update(
                    voice_url=webhook_url,
                    voice_method="POST"
                )
                print(f"✅ Successfully configured: {selected_number.phone_number}")
                print(f"   📡 Webhook URL: {webhook_url}")
                return selected_number.phone_number
                
            except Exception as e:
                print(f"❌ Error configuring number: {str(e)}")
                return None
                
    except Exception as e:
        print(f"❌ Error accessing Twilio numbers: {str(e)}")
        return None

def display_final_instructions(phone_number, tunnel_url):
    """Display final setup instructions"""
    print("\n" + "=" * 70)
    print("🎉 GENERAL VOICE ASSISTANT SETUP COMPLETED!")
    print("=" * 70)
    
    if phone_number:
        print(f"📞 Phone Number: {phone_number}")
    print(f"🌐 Webhook URL: {tunnel_url}/voice")
    print(f"🔍 Test Interface: {tunnel_url}/test")
    print(f"📊 Health Check: {tunnel_url}/health")
    
    print("\n📋 NEXT STEPS:")
    print("1. Keep this terminal running to maintain cloudflared tunnel")
    print("2. Start Flask app in another terminal: python app.py")
    if phone_number:
        print(f"3. Call {phone_number} to test the voice assistant")
    print("4. Ask any questions or request assistance")
    
    print("\n💡 SAMPLE QUESTIONS TO ASK:")
    print("• What can you help me with?")
    print("• Tell me about [any topic]")
    print("• How do I [perform any task]?")
    print("• Explain [any concept]")
    print("• Help me with [any request]")
    print("• What's the weather like?")
    print("• Give me some advice on [topic]")
    
    print("\n🔧 TECHNICAL FEATURES:")
    print("✓ Voice recognition via Twilio")
    print("✓ AI-powered responses (Groq/Gemini)")
    print("✓ ChromaDB knowledge base integration")
    print("✓ Conversation history tracking")
    print("✓ Natural language understanding")
    print("✓ Multi-turn conversations")
    print("✓ Graceful fallback mechanisms")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("• Responses are optimized for voice clarity")
    print("• ChromaDB server must be running at localhost:8000")
    print("• Knowledge base can be populated via ChromaDB API")
    print("• Conversation history is maintained per session")
    print("• Say 'goodbye' or 'bye' to end the call")
    
    print(f"\n🚀 Your General Voice Assistant is ready!")
    print("Press Ctrl+C to stop the cloudflared tunnel")

def main():
    """Main setup function"""
    print("🤖 GENERAL VOICE ASSISTANT - TWILIO SETUP")
    print("=" * 50)
    print("This will set up a voice-based AI assistant that can:")
    print("• Answer questions on any topic")
    print("• Provide information and explanations")
    print("• Help with tasks and requests")
    print("• Have natural conversations")
    print("• Access knowledge from ChromaDB")
    print("• Maintain conversation context")
    print("=" * 50)
    
    # Step 1: Check environment variables
    print("\n🔍 Step 1: Checking environment configuration...")
    if not check_environment():
        print("\n❌ Setup cannot continue without required environment variables")
        print("\n📝 Create a .env file with:")
        print("TWILIO_ACCOUNT_SID=your_account_sid")
        print("TWILIO_AUTH_TOKEN=your_auth_token")
        print("GEMINI_API_KEY=your_gemini_api_key")
        print("GROQ_API_KEY=your_groq_api_key")
        print("CHROMA_HOST=localhost")
        print("CHROMA_PORT=8000")
        return
    
    # Step 2: Check ChromaDB connection
    print("\n🔍 Step 2: Checking ChromaDB server connection...")
    chromadb_ok = check_chromadb_connection()
    if not chromadb_ok:
        print("\n⚠️  ChromaDB server is not running")
        print("The assistant will work but without knowledge base support")
        choice = input("\nContinue anyway? (y/n): ").strip().lower()
        if choice not in ['y', 'yes']:
            print("Setup cancelled. Please start ChromaDB server and try again.")
            return
    
    print("\n✅ Environment checks completed")
    
    # Step 3: Start cloudflared tunnel
    print("\n🔍 Step 3: Starting cloudflared tunnel...")
    tunnel_url = start_cloudflared()
    if not tunnel_url:
        print("\n❌ Failed to start cloudflared. Setup cancelled.")
        print("Make sure cloudflared is installed")
        return
    
    # Step 4: Test Flask application
    print("\n🔍 Step 4: Testing Flask application...")
    flask_running = test_flask_app(tunnel_url)
    if not flask_running:
        print("\n⚠️  Flask app is not responding")
        print("Make sure to run: python app.py")
        print("You can continue setup and start Flask later")
    
    # Step 5: Configure Twilio phone number
    print("\n🔍 Step 5: Configuring Twilio phone number...")
    phone_number = setup_twilio_phone(tunnel_url)
    
    # Step 6: Display final instructions
    display_final_instructions(phone_number, tunnel_url)
    
    # Keep running to maintain tunnel
    if phone_number or True:  # Always keep running
        try:
            print(f"\n🔄 Keeping tunnel active... (Ctrl+C to stop)")
            while True:
                time.sleep(60)
                # Ping health endpoint to keep services warm
                try:
                    requests.get(f"{tunnel_url}/health", timeout=5)
                except:
                    pass
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down voice assistant setup...")
            print("The phone number configuration is saved in Twilio")
            print("You can run this setup again anytime to get a new tunnel")
            print("\nTo restart the service:")
            print("1. Run: python twilio_setup.py")
            print("2. Run: python app.py")
    else:
        print("\n⚠️  Phone number configuration incomplete")
        print("You can configure manually in Twilio console:")
        print(f"Voice webhook URL: {tunnel_url}/voice")

if __name__ == "__main__":
    main()