#!/usr/bin/env python3
"""
Script to recreate the ChromaDB with persistent storage
Run this after switching from HttpClient to PersistentClient
"""

import os
import shutil
import subprocess
import sys

def check_chromadb_version():
    """Check ChromaDB version and provide compatibility info"""
    try:
        import chromadb
        version = chromadb.__version__
        print(f"📦 ChromaDB version: {version}")
        
        # Version compatibility info
        version_parts = version.split('.')
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        
        if major == 0 and minor < 4:
            print("⚠️  WARNING: ChromaDB version < 0.4.x detected")
            print("   PersistentClient may have different API")
            print("   Consider upgrading: pip install --upgrade chromadb")
        elif major == 0 and minor >= 4:
            print("✅ ChromaDB version is compatible with PersistentClient")
        else:
            print("ℹ️  Using newer ChromaDB version - should be compatible")
            
        return True
    except ImportError:
        print("❌ ChromaDB not installed")
        print("Install with: pip install chromadb")
        return False
    except Exception as e:
        print(f"⚠️  Could not check ChromaDB version: {e}")
        return True  # Continue anyway

def install_compatible_chromadb():
    """Install a known compatible version of ChromaDB"""
    print("🔄 Installing compatible ChromaDB version...")
    try:
        # Install a stable version that works well with PersistentClient
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "chromadb>=0.4.15,<0.5.0"
        ])
        print("✅ Compatible ChromaDB installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install ChromaDB: {e}")
        return False

def main():
    print("🔄 Recreating ChromaDB with Persistent Storage")
    print("=" * 50)
    
    # Check ChromaDB version compatibility
    if not check_chromadb_version():
        if input("Install ChromaDB? (y/n): ").lower().startswith('y'):
            if not install_compatible_chromadb():
                return
        else:
            print("❌ ChromaDB required. Exiting.")
            return
    
    # Remove existing chroma_db directory if it exists
    if os.path.exists("./chroma_db"):
        print("🗑️  Removing existing chroma_db directory...")
        shutil.rmtree("./chroma_db")
        print("✅ Removed existing database")
    
    # Run the knowledge base setup
    print("🚀 Running knowledge base setup with persistent storage...")
    try:
        # Import here to ensure we have the right version
        import chromadb
        print(f"📦 Using ChromaDB {chromadb.__version__}")
        
        exec(open("knowledge_base_setup.py").read())
        print("✅ Database recreated successfully!")
        print("")
        print("🎉 Setup Complete!")
        print("📁 Database stored in: ./chroma_db")
        print("🔗 No server needed - database is embedded in your application")
        print("")
        print("Version Compatibility Notes:")
        print("- HttpClient format: Server-based storage")
        print("- PersistentClient format: File-based storage")
        print("- Data formats are incompatible between modes")
        print("")
        print("Next steps:")
        print("1. Run: python app.py")
        print("2. Test: http://localhost:5000/test")
        
    except Exception as e:
        print(f"❌ Error recreating database: {e}")
        print("")
        print("Troubleshooting:")
        print("1. Check ChromaDB version compatibility")
        print("2. Try: pip install --upgrade chromadb")
        print("3. Or install specific version: pip install chromadb==0.4.15")
        print("4. Ensure all dependencies: pip install flask twilio python-dotenv requests groq")

if __name__ == "__main__":
    main()