"""Comprehensive endpoint validation for VoiceFlow Python backend."""
import requests
import json
import sys

BASE = "http://127.0.0.1:8000"
H = {"x-tenant-id": "demo-tenant", "Content-Type": "application/json"}
AGENT_ID = "9f807ac4-9928-49fa-b81b-7fe342c98c14"

results = []


def test(name, method, path, expected_status=200, json_body=None, data=None, files=None, extra_headers=None):
    url = f"{BASE}{path}"
    headers = {k: v for k, v in H.items()}
    if extra_headers:
        headers.update(extra_headers)
    if files:
        headers.pop("Content-Type", None)
    try:
        r = getattr(requests, method)(url, headers=headers, json=json_body, data=data, files=files, timeout=30)
        status = "PASS" if r.status_code == expected_status else "FAIL"
        results.append((name, status, r.status_code, expected_status))
        symbol = "+" if status == "PASS" else "X"
        print(f"  [{symbol}] {name}: {r.status_code} (expected {expected_status})")
        return r
    except Exception as e:
        results.append((name, "ERROR", str(e), expected_status))
        print(f"  [!] {name}: ERROR - {e}")
        return None


print("=" * 70)
print("VoiceFlow Python Backend - Comprehensive Endpoint Validation")
print("=" * 70)

print("\n--- Health ---")
test("Health Check", "get", "/health")

print("\n--- Auth ---")
test("Signup", "post", "/auth/signup", 200, {"email": "test@test.com", "password": "pass123"})
test("Login", "post", "/auth/login", 200, {"email": "test@test.com", "password": "pass123"})

print("\n--- Templates ---")
test("List Templates", "get", "/api/templates/")

print("\n--- Agents ---")
test("List Agents", "get", "/api/agents/")
test("Get Agent", "get", f"/api/agents/{AGENT_ID}")
test("Update Agent", "put", f"/api/agents/{AGENT_ID}", 200, {"name": "Test Agent E2E"})

print("\n--- Brands ---")
test("List Brands", "get", "/api/brands/")
r = test("Create Brand", "post", "/api/brands/", 201, {"name": "Test Brand Validation", "primaryColor": "#FF0000"})
if r and r.status_code == 201:
    brand_id = r.json().get("id")
    test("Get Brand", "get", f"/api/brands/{brand_id}")
    test("Update Brand", "put", f"/api/brands/{brand_id}", 200, {"name": "Updated Brand"})
    test("Delete Brand", "delete", f"/api/brands/{brand_id}")

print("\n--- Documents ---")
test("List Documents", "get", f"/api/documents/?agentId={AGENT_ID}")
test("Create Document (URL)", "post", "/api/documents/", 201, {"agentId": AGENT_ID, "url": "https://example.com"})
r = test("Upload Document (file)", "post", "/api/documents/upload", 201,
         files={"file": ("test.txt", b"VoiceFlow test document content for validation.", "text/plain")},
         data={"agentId": AGENT_ID})

print("\n--- Ingestion ---")
test("Start Ingestion", "post", "/api/ingestion/start", 200, {"agentId": AGENT_ID, "urls": ["https://example.com"]})
test("Company Crawl", "post", "/api/ingestion/company", 200, {"agentId": AGENT_ID, "websiteUrl": "https://example.com"})
test("List Jobs", "get", f"/api/ingestion/jobs?agentId={AGENT_ID}")

print("\n--- RAG ---")
test("RAG Query", "post", "/api/rag/query", 200, {"agentId": AGENT_ID, "query": "What is VoiceFlow?"})
test("RAG Conversation", "get", "/api/rag/conversation/test-session")

print("\n--- Analytics ---")
test("Analytics Overview", "get", "/analytics/overview")
test("Call Analytics", "get", "/analytics/calls")

print("\n--- Retraining ---")
test("List Retraining", "get", "/api/retraining/")
test("Retraining Stats", "get", "/api/retraining/stats")

print("\n--- Settings ---")
test("Get Twilio Settings", "get", "/api/settings/twilio")
test("Get Groq Settings", "get", "/api/settings/groq")
test("List Models", "get", "/api/settings/groq/models")

print("\n--- Onboarding ---")
test("Get Progress", "get", "/onboarding/progress")
test("Save Progress", "post", "/onboarding/progress", 200, {"step": "create-agent", "completed": True})

print("\n--- Widget ---")
test("Widget Config", "get", f"/api/widget/{AGENT_ID}")
r_ws = test("Widget Session", "post", f"/api/widget/{AGENT_ID}/sessions", 200)
widget_sess = r_ws.json().get("sessionId", "val-sess") if r_ws and r_ws.status_code == 200 else "val-sess"
test("Widget Message", "post", f"/api/widget/{AGENT_ID}/sessions/{widget_sess}/message", 200, {"message": "Hello"})
test("Widget Transcript", "get", f"/api/widget/{AGENT_ID}/sessions/{widget_sess}")

print("\n--- Admin ---")
test("Admin Pipelines", "get", "/admin/pipelines")
test("Admin Agents", "get", "/admin/pipeline_agents")

print("\n--- Users ---")
test("List Users", "get", "/api/users/")

print("\n--- Logs ---")
test("List Logs", "get", "/api/logs/")

print("\n--- TTS ---")
test("TTS Synthesise", "post", "/api/tts/synthesise", expected_status=502, json_body={"text": "hello", "voice": "female"})
test("TTS Preset Voices", "get", "/api/tts/preset-voices", expected_status=502)

print("\n" + "=" * 70)
passed = sum(1 for _, s, _, _ in results if s == "PASS")
failed = sum(1 for _, s, _, _ in results if s == "FAIL")
errors = sum(1 for _, s, _, _ in results if s == "ERROR")
total = len(results)
print(f"RESULTS: {passed}/{total} passed, {failed} failed, {errors} errors")
print("=" * 70)

if failed > 0:
    print("\nFAILED TESTS:")
    for name, status, actual, expected in results:
        if status == "FAIL":
            print(f"  - {name}: got {actual}, expected {expected}")

if errors > 0:
    print("\nERRORS:")
    for name, status, actual, expected in results:
        if status == "ERROR":
            print(f"  - {name}: {actual}")

sys.exit(1 if failed > 0 or errors > 0 else 0)
