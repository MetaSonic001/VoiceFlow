# ChromaDB Version Compatibility Guide

## Key Differences Between HttpClient and PersistentClient

### HttpClient Mode (Your Previous Setup)
- **ChromaDB Version**: Works with most versions
- **Storage**: Server-based, requires separate ChromaDB server
- **Connection**: `chromadb.HttpClient(host="localhost", port=8000)`
- **Data Format**: Network protocol format
- **Startup**: Need to run `chroma run --host localhost --port 8000`

### PersistentClient Mode (New Setup)
- **ChromaDB Version**: Requires 0.4.0+ for stable API
- **Storage**: File-based, embedded in application
- **Connection**: `chromadb.PersistentClient(path="./chroma_db")`
- **Data Format**: SQLite + file storage
- **Startup**: No separate server needed

## Version Compatibility Issues

### ChromaDB < 0.4.0
- ❌ `PersistentClient` API may be different or unstable
- ❌ Embedding functions may have different imports
- ❌ Collection creation syntax differs

### ChromaDB 0.4.0 - 0.4.14
- ⚠️ Basic `PersistentClient` support
- ⚠️ Some stability issues with concurrent access
- ✅ Can work but may have bugs

### ChromaDB 0.4.15+ (Recommended)
- ✅ Stable `PersistentClient` API
- ✅ Better performance and reliability
- ✅ Consistent embedding functions
- ✅ Proper metadata handling

### ChromaDB 0.5.0+
- ⚠️ May have breaking API changes
- ⚠️ Test before upgrading
- ✅ Generally backward compatible

## Migration Issues You Might Face

### 1. Database Format Incompatibility
**Problem**: Cannot read HttpClient database with PersistentClient
```
chromadb.errors.InvalidDimensionException: Expected dimensionality...
```
**Solution**: Delete old database and recreate (that's why we have the recreate script)

### 2. API Changes
**Problem**: Method signatures changed between versions
```
TypeError: create_collection() got an unexpected keyword argument
```
**Solution**: Upgrade to compatible version: `pip install chromadb>=0.4.15,<0.5.0`

### 3. Embedding Function Changes
**Problem**: Import paths changed
```
ImportError: cannot import name 'DefaultEmbeddingFunction'
```
**Solution**: Update imports based on version:
```python
# Newer versions
from chromadb.utils import embedding_functions
embedding_function = embedding_functions.DefaultEmbeddingFunction()

# Older versions might use
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
embedding_function = DefaultEmbeddingFunction()
```

## Recommended Installation

For maximum compatibility with your current code:

```bash
# Uninstall existing ChromaDB
pip uninstall chromadb chromadb-client

# Install compatible version
pip install chromadb>=0.4.15,<0.5.0

# Verify installation
python -c "import chromadb; print(chromadb.__version__)"
```

## Quick Fix Commands

If you encounter issues:

```bash
# Reset everything
pip uninstall chromadb chromadb-client
pip install chromadb==0.4.24
rm -rf ./chroma_db
python recreate_persistent_db.py
```

## Testing Compatibility

Run this to test your setup:

```python
import chromadb
from chromadb.utils import embedding_functions

print(f"ChromaDB version: {chromadb.__version__}")

# Test PersistentClient
client = chromadb.PersistentClient(path="./test_db")
collection = client.create_collection(
    name="test", 
    embedding_function=embedding_functions.DefaultEmbeddingFunction()
)
print("✅ PersistentClient working!")

# Cleanup
client.delete_collection("test")
```

The recreate script now handles these version checks automatically!