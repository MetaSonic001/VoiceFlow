#!/usr/bin/env python3
"""
FR CRCE Information System - Complete Setup Guide
This script guides you through the entire setup process
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"You have Python {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} - Compatible")
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    print("📝 Creating .env file...")
    
    env_template = """# FR CRCE Information System Environment Variables
# Replace the placeholder values with your actual API keys

# Twilio Configuration (Get from https://console.twilio.com/)
TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

# Groq API Key (Get from https://console.groq.com/)
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Key (Get from https://makersuite.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional Configuration
PORT=5000
WEBSOCKET_PORT=8080
GROQ_MODEL=llama-3.1-8b-instant
CHROMA_DB_PATH=./chroma_db
"""
    
    with open(env_file, "w") as f:
        f.write(env_template)
    
    print("✅ Created .env file")
    return True

def check_required_packages():
    """Check if all required packages are installed"""
    required_packages = [
        "flask", "twilio", "chromadb", "requests", 
        "python-dotenv", "pandas"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} - Installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - Missing")
    
    if missing_packages:
        print(f"\n📦 Install missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_env_variables():
    """Check if environment variables are set"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'TWILIO_ACCOUNT_SID': 'https://console.twilio.com/',
        'TWILIO_AUTH_TOKEN': 'https://console.twilio.com/', 
        'GROQ_API_KEY': 'https://console.groq.com/',
        'GEMINI_API_KEY': 'https://makersuite.google.com/app/apikey'
    }
    
    missing_vars = []
    
    for var, source in required_vars.items():
        value = os.environ.get(var)
        if not value or value.startswith('your_'):
            missing_vars.append((var, source))
            print(f"❌ {var} - Not set")
        else:
            print(f"✅ {var} - Configured")
    
    if missing_vars:
        print(f"\n🔑 Please add these API keys to your .env file:")
        for var, source in missing_vars:
            print(f"  - {var} from {source}")
        return False
    
    return True

def setup_knowledge_base():
    """Run the knowledge base setup"""
    print("\n📚 Setting up FR CRCE knowledge base...")
    
    if Path("chroma_db").exists():
        print("✅ ChromaDB directory already exists")
    
    try:
        print("Running knowledge base setup...")
        os.system("python frcrce_knowledge_setup.py")
        print("✅ Knowledge base setup completed")
        return True
    except Exception as e:
        print(f"❌ Knowledge base setup failed: {e}")
        return False

def main():
    print("=" * 60)
    print("FR CRCE INFORMATION SYSTEM - SETUP GUIDE")
    print("=" * 60)
    
    print("\n🔍 Step 1: Checking Python version...")
    if not check_python_version():
        return
    
    print("\n📦 Step 2: Checking required packages...")
    if not check_required_packages():
        print("\n❌ Please install missing packages first!")
        return
    
    print("\n📝 Step 3: Creating environment file...")
    create_env_file()
    
    print("\n🔑 Step 4: Checking API keys...")
    if not check_env_variables():
        print("\n❌ Please configure your API keys in the .env file!")
        print("Then run this script again.")
        return
    
    print("\n📚 Step 5: Setting up knowledge base...")
    if not setup_knowledge_base():
        print("❌ Knowledge base setup failed!")
        return
    
    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\n📋 Next steps:")
    print("1. Run: python twilio_setup.py")
    print("   (This will set up ngrok and configure your Twilio phone number)")
    
    print("\n2. In a separate terminal, run: python app.py")
    print("   (This starts the Flask application)")
    
    print("\n3. Optionally run: node server.js")
    print("   (This starts the WebSocket server for the dashboard)")
    
    print("\n💡 Testing:")
    print("- Test locally: http://localhost:5000/test")
    print("- Call your Twilio number to test voice interactions")
    
    print("\n📞 Your system will be ready to handle voice calls about FR CRCE!")

if __name__ == "__main__":
    main()