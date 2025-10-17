#!/usr/bin/env python3
"""
ChromaDB Data Cleanup Script
Erases all data from ChromaDB collections
"""

import os
import sys
from chromadb import HttpClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")

def clear_chromadb():
    """Clear all data from ChromaDB"""
    
    print("🗑️  ChromaDB Data Cleanup Utility")
    print("=" * 50)
    print(f"Target: {CHROMA_HOST}:{CHROMA_PORT}")
    print("=" * 50)
    
    try:
        # Connect to ChromaDB
        client = HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
        
        # Get all collections
        collections = client.list_collections()
        
        if not collections:
            print("\n✅ No collections found. ChromaDB is already empty.")
            return
        
        print(f"\n📚 Found {len(collections)} collection(s):")
        for i, col in enumerate(collections, 1):
            try:
                count = client.get_collection(col.name).count()
                print(f"   {i}. {col.name} ({count} documents)")
            except:
                print(f"   {i}. {col.name} (unknown count)")
        
        print("\n⚠️  WARNING: This will permanently delete ALL data!")
        print("This action cannot be undone.")
        
        # Confirm deletion
        confirm = input("\nType 'DELETE' to confirm: ").strip()
        
        if confirm != "DELETE":
            print("\n❌ Deletion cancelled. No changes made.")
            return
        
        # Delete all collections
        print("\n🗑️  Deleting collections...")
        deleted_count = 0
        
        for col in collections:
            try:
                client.delete_collection(col.name)
                print(f"   ✅ Deleted: {col.name}")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ Failed to delete {col.name}: {str(e)}")
        
        print(f"\n✅ Successfully deleted {deleted_count}/{len(collections)} collection(s)")
        print("ChromaDB is now empty.")
        
    except ConnectionError:
        print(f"\n❌ Error: Cannot connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        print("\n📝 Make sure ChromaDB server is running:")
        print("   chroma run --host localhost --port 8000")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

def clear_specific_collection(collection_name: str):
    """Clear a specific collection"""
    
    print(f"🗑️  Clearing Collection: {collection_name}")
    print("=" * 50)
    
    try:
        client = HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
        
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            
            print(f"\n📚 Collection: {collection_name}")
            print(f"   Documents: {count}")
            
            if count == 0:
                print("\n✅ Collection is already empty.")
                
                # Ask if they want to delete the empty collection
                delete_empty = input("\nDelete the empty collection? (y/n): ").strip().lower()
                if delete_empty in ['y', 'yes']:
                    client.delete_collection(collection_name)
                    print(f"✅ Deleted collection: {collection_name}")
                return
            
            print("\n⚠️  WARNING: This will delete all documents in this collection!")
            confirm = input(f"\nType '{collection_name}' to confirm: ").strip()
            
            if confirm != collection_name:
                print("\n❌ Deletion cancelled.")
                return
            
            # Delete and recreate collection
            client.delete_collection(collection_name)
            print(f"✅ Deleted collection: {collection_name}")
            
            # Recreate empty collection
            client.create_collection(
                name=collection_name,
                metadata={"description": "General knowledge base for voice agent", "hnsw:space": "cosine"}
            )
            print(f"✅ Recreated empty collection: {collection_name}")
            
        except Exception as e:
            if "does not exist" in str(e).lower():
                print(f"\n❌ Collection '{collection_name}' does not exist.")
            else:
                raise
                
    except ConnectionError:
        print(f"\n❌ Error: Cannot connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        # Clear specific collection
        collection_name = sys.argv[1]
        clear_specific_collection(collection_name)
    else:
        # Clear all collections
        clear_chromadb()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user.")
        sys.exit(0)
