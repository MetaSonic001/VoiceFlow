import requests
import time

# Test URLs
test_urls = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://www.bbc.com/news",
    "https://github.com/microsoft/vscode",
]

# Test data
test_data = {
    "tenantId": "test-tenant-123",
    "agentId": "test-agent-456",
    "urls": test_urls,
    "s3_urls": []
}

# Start ingestion
response = requests.post("http://localhost:8001/ingest", json=test_data)
if response.status_code == 200:
    job_id = response.json()["job_id"]
    print(f"Ingestion started with job ID: {job_id}")

    # Poll for status
    while True:
        status_response = requests.get(f"http://localhost:8001/status/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Status: {status_data['status']}, Progress: {status_data.get('progress', 'N/A')}%")
            if status_data['status'] in ['completed', 'failed']:
                break
        time.sleep(5)
else:
    print(f"Failed to start ingestion: {response.status_code}, {response.text}")

print("Test completed!")