import requests, json
TENANT = "demo-tenant"
AGENT_ID = "9f807ac4-9928-49fa-b81b-7fe342c98c14"
BASE = "http://127.0.0.1:8000"
H = {"x-tenant-id": TENANT}

r = requests.get(f"{BASE}/api/documents", headers=H, params={"agentId": AGENT_ID})
docs = r.json()
if isinstance(docs, list):
    for d in docs:
        did = str(d.get("id", "?"))[:12]
        title = d.get("title", d.get("name", "?"))
        status = d.get("status", "?")
        created = str(d.get("createdAt", ""))[:19]
        print(f"  {did}... | {title} | {status} | {created}")
else:
    print(json.dumps(docs, indent=2)[:500])
