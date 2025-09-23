import os
import sys
from twilio.rest import Client
import subprocess
import time
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "GROQ_API_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Please set them in your .env file:")
        for var in missing:
            if var == "GROQ_API_KEY":
                print(f"{var}=your_groq_api_key_from_console.groq.com")
            else:
                print(f"{var}=your_{var.lower()}_from_twilio_console")
        return False
    return True

def check_knowledge_base():
    """Check if the FR CRCE knowledge base is set up"""
    import chromadb
    from chromadb.utils import embedding_functions
    
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)  # Use HttpClient
        embedding_function = embedding_functions.DefaultEmbeddingFunction()
        collection = client.get_collection(
            name="frcrce_knowledge",
            embedding_function=embedding_function
        )
        
        # Test if the collection has documents
        count = collection.count()
        if count == 0:
            print("Warning: FR CRCE knowledge base exists but is empty.")
            print("Please run the knowledge base setup script to populate it.")
            return False
        
        print(f"✓ FR CRCE knowledge base found with {count} documents")
        return True
        
    except Exception as e:
        print("Error: FR CRCE knowledge base not found.")
        print("Please run the knowledge base setup script first:")
        print("python frcrce_knowledge_setup.py")
        return False

def start_ngrok(port=5000):
    """Start ngrok and return the public URL"""
    print(f"Starting ngrok on port {port}...")
    
    # Check if ngrok is installed
    try:
        subprocess.run(["ngrok", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ngrok is not installed or not in PATH.")
        print("Please install ngrok from https://ngrok.com/download")
        print("\nOn Windows: Download and extract ngrok.exe to your PATH")
        print("On macOS: brew install ngrok")
        print("On Linux: Download and extract to /usr/local/bin/")
        return None
    
    # Kill any existing ngrok processes
    try:
        subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
        time.sleep(1)
    except:
        pass
    
    # Start ngrok process
    ngrok_process = subprocess.Popen(
        ["ngrok", "http", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for ngrok to start
    print("Waiting for ngrok to start...")
    time.sleep(4)
    
    # Get ngrok URL
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=10)
        data = response.json()
        
        if not data.get("tunnels"):
            print("Error: No ngrok tunnels found.")
            print("Make sure ngrok started successfully.")
            return None
        
        # Get HTTPS URL
        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        
        # Fallback to HTTP if HTTPS not found
        return data["tunnels"][0]["public_url"]
    except Exception as e:
        print(f"Error getting ngrok URL: {str(e)}")
        print("Make sure ngrok is running and accessible at http://localhost:4040")
        return None

def setup_twilio_number(ngrok_url):
    """Configure a Twilio phone number to use our webhook URLs"""
    if not check_environment():
        return None
    
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    
    try:
        client = Client(account_sid, auth_token)
        
        # Test Twilio credentials
        account = client.api.accounts(account_sid).fetch()
        print(f"✓ Connected to Twilio account: {account.friendly_name}")
        
    except Exception as e:
        print(f"Error connecting to Twilio: {str(e)}")
        print("Please check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        return None
    
    # Get available phone numbers
    try:
        numbers = client.incoming_phone_numbers.list()
        
        if not numbers:
            print("\nNo phone numbers found in your Twilio account.")
            print("You need to purchase a phone number to use this service.")
            print("\nWould you like to search for available numbers? (y/n)")
            choice = input().lower().strip()
            
            if choice == 'y':
                # Get available numbers
                print("\nAvailable countries:")
                print("IN - India")
                print("US - United States")
                print("GB - United Kingdom")
                print("CA - Canada")
                
                country_code = input("\nEnter country code (default: IN): ").upper().strip() or "IN"
                
                try:
                    available_numbers = client.available_phone_numbers(country_code).local.list(limit=10)
                    
                    if not available_numbers:
                        print(f"No numbers available for country code {country_code}.")
                        print("Try a different country code or check your Twilio account balance.")
                        return None
                    
                    print(f"\nAvailable phone numbers in {country_code}:")
                    for i, number in enumerate(available_numbers[:5]):  # Show only first 5
                        print(f"{i+1}. {number.phone_number} - {number.friendly_name}")
                    
                    selection = input(f"\nSelect a number to purchase (1-{min(5, len(available_numbers))}): ").strip()
                    
                    try:
                        selection = int(selection) - 1
                        if 0 <= selection < len(available_numbers):
                            selected_number = available_numbers[selection]
                            print(f"\nPurchasing {selected_number.phone_number}...")
                            
                            number = client.incoming_phone_numbers.create(
                                phone_number=selected_number.phone_number,
                                voice_url=f"{ngrok_url}/voice"
                            )
                            print(f"✓ Successfully purchased and configured {number.phone_number}")
                            return number.phone_number
                        else:
                            print("Invalid selection")
                            return None
                    except ValueError:
                        print("Please enter a valid number")
                        return None
                        
                except Exception as e:
                    print(f"Error searching for numbers: {str(e)}")
                    if "does not appear to be a valid country code" in str(e):
                        print("Please use a valid country code like IN, US, GB, CA")
                    return None
            else:
                print("Setup cancelled. You need a phone number to proceed.")
                return None
        else:
            print(f"\n✓ Found {len(numbers)} existing phone number(s) in your account:")
            for i, number in enumerate(numbers):
                print(f"{i+1}. {number.phone_number} ({number.friendly_name})")
            
            if len(numbers) == 1:
                choice = input(f"\nConfigure {numbers[0].phone_number} for FR CRCE info service? (y/n): ").lower().strip()
                if choice == 'y':
                    selected_number = numbers[0]
                else:
                    print("Setup cancelled")
                    return None
            else:
                selection = input(f"\nSelect a number to configure (1-{len(numbers)}): ").strip()
                try:
                    selection = int(selection) - 1
                    if 0 <= selection < len(numbers):
                        selected_number = numbers[selection]
                    else:
                        print("Invalid selection")
                        return None
                except ValueError:
                    print("Please enter a valid number")
                    return None
            
            # Configure the selected number
            try:
                selected_number.update(voice_url=f"{ngrok_url}/voice")
                print(f"✓ Successfully configured {selected_number.phone_number}")
                print(f"  Voice webhook URL: {ngrok_url}/voice")
                return selected_number.phone_number
            except Exception as e:
                print(f"Error configuring number: {str(e)}")
                return None
                
    except Exception as e:
        print(f"Error accessing Twilio numbers: {str(e)}")
        return None

def test_webhook_endpoint(ngrok_url):
    """Test if the Flask app webhook endpoint is responding"""
    try:
        test_url = f"{ngrok_url}/test_webhook"
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✓ Webhook endpoint is responding: {test_url}")
            return True
        else:
            print(f"⚠ Webhook endpoint returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠ Could not reach webhook endpoint: {str(e)}")
        print("Make sure your Flask app is running on port 5000")
        return False

def main():
    print("FR CRCE College Information System - Twilio Setup")
    print("=" * 50)
    print("This will set up a voice-based information system for FR CRCE college")
    print("Students and parents can call to get information about:")
    print("- Admission process and requirements")
    print("- Fee structure and scholarships")
    print("- Courses and programs offered")
    print("- Campus facilities and placements")
    print("- Location and contact information")
    print("=" * 50)
    
    # Check environment variables
    if not check_environment():
        print("\n❌ Setup cannot continue without required environment variables")
        return
    
    # Check if knowledge base is ready
    if not check_knowledge_base():
        print("\n❌ Setup cannot continue without the FR CRCE knowledge base")
        return
    
    print("\n✓ Environment and knowledge base checks passed")
    
    # Start ngrok to get public URL
    ngrok_url = start_ngrok()
    if not ngrok_url:
        print("\n❌ Failed to start ngrok. Setup cancelled.")
        return
    
    print(f"\n✓ Ngrok tunnel established: {ngrok_url}")
    
    # Test webhook endpoint
    print("\nTesting webhook endpoint...")
    if not test_webhook_endpoint(ngrok_url):
        print("\n⚠ Warning: Webhook endpoint is not responding")
        print("Make sure to start your Flask app with: python app.py")
    
    # Configure Twilio number
    print("\nConfiguring Twilio phone number...")
    phone_number = setup_twilio_number(ngrok_url)
    
    if phone_number:
        print("\n" + "=" * 50)
        print("🎉 Setup Complete!")
        print("=" * 50)
        print(f"📞 Phone Number: {phone_number}")
        print(f"🌐 Webhook URL: {ngrok_url}/voice")
        print(f"🔍 Test URL: {ngrok_url}/test")
        print(f"📊 Health Check: {ngrok_url}/health")
        
        print("\n📋 Next Steps:")
        print("1. Keep this terminal running to maintain the ngrok tunnel")
        print("2. Start your Flask app: python app.py")
        print(f"3. Call {phone_number} to test the system")
        print("4. Try asking about fees, courses, placements, or location")
        
        print("\n💡 Tips:")
        print("- Speak clearly and pause between sentences")
        print("- Ask one question at a time for best results")
        print("- Say 'thank you' or 'goodbye' to end the call")
        
        print(f"\n🚀 Your FR CRCE information system is ready!")
        print("Press Ctrl+C to stop the ngrok tunnel")
        
        # Keep the script running to maintain ngrok
        try:
            while True:
                time.sleep(60)
                # Optional: ping the health endpoint to keep services warm
                try:
                    requests.get(f"{ngrok_url}/health", timeout=5)
                except:
                    pass
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            print("The phone number configuration will persist in your Twilio account")
            print("You can run this setup again anytime to get a new ngrok URL")
    else:
        print("\n❌ Failed to configure Twilio phone number")
        print("Please check your Twilio account and try again")

if __name__ == "__main__":
    main()