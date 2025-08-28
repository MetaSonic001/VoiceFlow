# debug_api.py
# Quick debug script to identify and fix API issues

import requests
import json
import sqlite3
import os

API_BASE = "http://localhost:8000"

def check_api_health():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"✅ API Health: {response.status_code} - {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ API not running. Start with: python main.py")
        return False
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False

def check_database():
    """Check database status"""
    if os.path.exists("voiceflow.db"):
        try:
            conn = sqlite3.connect("voiceflow.db")
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"✅ Database exists with {len(tables)} tables: {[t[0] for t in tables]}")
            
            # Check data
            for table in ['companies', 'users', 'agents', 'documents']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0] if isinstance(table, tuple) else table};")
                    count = cursor.fetchone()[0]
                    print(f"  - {table}: {count} records")
                except:
                    pass
            
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    else:
        print("⚠️ Database not found (will be created on first API start)")
        return False

def test_signup():
    """Test user signup"""
    try:
        data = {
            "email": "debug@test.com",
            "password": "debug123",
            "company_name": "Debug Company",
            "industry": "Testing"
        }
        
        response = requests.post(f"{API_BASE}/auth/signup", json=data, timeout=10)
        print(f"Signup Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Signup successful: {result}")
            return result.get('access_token')
        else:
            print(f"❌ Signup failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return None

def test_login():
    """Test user login"""
    try:
        data = {
            "email": "debug@test.com",
            "password": "debug123"
        }
        
        response = requests.post(f"{API_BASE}/auth/login", json=data, timeout=10)
        print(f"Login Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Login successful")
            print(f"Token: {result.get('access_token', 'Not found')}")
            print(f"Session ID: {result.get('session_id', 'Not found')}")
            return result
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_authenticated_endpoint(token):
    """Test authenticated endpoint"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
        
        print(f"Auth test Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Authentication working: {response.json()}")
            return True
        else:
            print(f"❌ Auth failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Auth test error: {e}")
        return False

def test_knowledge_upload(token):
    """Test knowledge upload"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "text_content": "This is a test document. Our company provides excellent service. Contact us at test@company.com for support."
        }
        
        response = requests.post(f"{API_BASE}/onboarding/knowledge", 
                               headers=headers, json=data, timeout=30)
        
        print(f"Knowledge upload Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Knowledge upload working: {response.json()}")
            return True
        else:
            print(f"❌ Knowledge upload failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Knowledge upload error: {e}")
        return False

def test_conversation(token, session_id):
    """Test conversation with CrewAI"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "content": "What services does the company provide?",
            "type": "text"
        }
        
        response = requests.post(f"{API_BASE}/conversations/{session_id}/message", 
                               headers=headers, json=data, timeout=60)
        
        print(f"Conversation Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Conversation working")
            print(f"Response: {result.get('response', 'No response')}")
            return True
        else:
            print(f"❌ Conversation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Conversation error: {e}")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'crewai', 'PyPDF2', 
        'scikit-learn', 'numpy', 'python-jose', 'python-multipart'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}: installed")
        except ImportError:
            print(f"❌ {package}: missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n🔧 Install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    print("🔍 VoiceFlow AI API Debug Tool")
    print("===============================")
    
    print("\n1. Checking Dependencies...")
    deps_ok = check_dependencies()
    
    print("\n2. Checking Database...")
    check_database()
    
    print("\n3. Checking API Health...")
    if not check_api_health():
        return
    
    print("\n4. Testing Signup...")
    token = test_signup()
    
    if not token:
        print("\n5. Trying Login instead...")
        login_result = test_login()
        if login_result:
            token = login_result.get('access_token')
            session_id = login_result.get('session_id')
        else:
            print("❌ Both signup and login failed. Check API logs.")
            return
    else:
        # If signup worked, try login to get session
        print("\n5. Getting Session ID...")
        login_result = test_login()
        session_id = login_result.get('session_id') if login_result else None
    
    if token:
        print("\n6. Testing Authentication...")
        auth_ok = test_authenticated_endpoint(token)
        
        if auth_ok:
            print("\n7. Testing Knowledge Upload...")
            knowledge_ok = test_knowledge_upload(token)
            
            if session_id:
                print(f"\n8. Testing Conversation (Session: {session_id})...")
                conv_ok = test_conversation(token, session_id)
            else:
                print("\n8. ❌ No session ID for conversation test")
    
    print("\n" + "="*50)
    print("🎉 Debug Complete!")
    print("\nIf you see errors above:")
    print("1. Check the FastAPI server terminal for detailed error logs")
    print("2. Make sure all dependencies are installed")
    print("3. Try resetting the database: rm voiceflow.db")
    print("4. Restart the FastAPI server")

if __name__ == "__main__":
    main()