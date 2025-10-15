import sys
import os
sys.path.append('agent-workflow')

from app import get_agent

# Test agent retrieval for different tenant/agent combinations
print("Testing agent initialization for different tenant/agent combinations...")

# Test default agent (no tenant/agent)
print("\n1. Testing default agent:")
agent_default = get_agent()
if agent_default:
    print(f"   Collection: {agent_default.collection.name}")
    print(f"   Document count: {agent_default.collection.count()}")
else:
    print("   Failed to initialize")

# Test with tenant/agent IDs (using one of the collections we saw)
tenant_id = "b116592b-263d-430d-9ff1-253e2fc5b6dd"
agent_id = "a55dcf58-e1d5-4cbc-80a1-5a6264988873"

print(f"\n2. Testing tenant/agent specific agent ({tenant_id}/{agent_id}):")
agent_tenant = get_agent(tenant_id, agent_id)
if agent_tenant:
    print(f"   Collection: {agent_tenant.collection.name}")
    print(f"   Document count: {agent_tenant.collection.count()}")
else:
    print("   Failed to initialize")

# Test query on the tenant-specific collection
if agent_tenant:
    print("\n3. Testing query on tenant-specific collection:")
    try:
        result = agent_tenant.search_embeddings("test query")
        print(f"   Query successful: {result.get('found', False)}")
        print(f"   Documents found: {len(result.get('documents', []))}")
    except Exception as e:
        print(f"   Query failed: {e}")

# Test default agent (no tenant/agent)
print("\n1. Testing default agent:")
agent_default = get_agent()
if agent_default:
    print(f"   Collection: {agent_default.collection.name}")
    print(f"   Document count: {agent_default.collection.count()}")
else:
    print("   Failed to initialize")

# Test with tenant/agent IDs (using one of the collections we saw)
tenant_id = "b116592b-263d-430d-9ff1-253e2fc5b6dd"
agent_id = "a55dcf58-e1d5-4cbc-80a1-5a6264988873"

print(f"\n2. Testing tenant/agent specific agent ({tenant_id}/{agent_id}):")
agent_tenant = get_agent(tenant_id, agent_id)
if agent_tenant:
    print(f"   Collection: {agent_tenant.collection.name}")
    print(f"   Document count: {agent_tenant.collection.count()}")
else:
    print("   Failed to initialize")

# Test query on the tenant-specific collection
if agent_tenant:
    print("\n3. Testing query on tenant-specific collection:")
    try:
        result = agent_tenant.search_embeddings("test query")
        print(f"   Query successful: {result.get('found', False)}")
        print(f"   Documents found: {len(result.get('documents', []))}")
    except Exception as e:
        print(f"   Query failed: {e}")