import asyncio
import httpx
import json

async def test_ingestion():
    """Test the full ingestion pipeline"""
    base_url = "http://localhost:8001"

    # Test data
    test_data = {
        "urls": ["https://en.wikipedia.org/wiki/Artificial_intelligence"],
        "agent_id": "test-agent-123",
        "user_id": "test-user-123"
    }

    async with httpx.AsyncClient() as client:
        try:
            # Start ingestion
            print("Starting ingestion...")
            response = await client.post(
                f"{base_url}/ingest",
                json=test_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                job_id = result.get("job_id")
                print(f"Ingestion started with job ID: {job_id}")

                # Check status
                print("Checking status...")
                status_response = await client.get(f"{base_url}/status/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"Status: {status.get('status')}")
                    if status.get('status') == 'completed':
                        print("Ingestion completed successfully!")
                    else:
                        print(f"Ingestion status: {status}")
                else:
                    print(f"Failed to get status: {status_response.status_code}")
            else:
                print(f"Failed to start ingestion: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ingestion())