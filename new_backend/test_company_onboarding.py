"""
Company onboarding integration tests
======================================
Tests the FULL company-onboarding pipeline end-to-end:

  [Express]  GET  /onboarding/company-search       → seed-list typeahead
  [Express]  POST /onboarding/company              → save to Postgres + trigger FastAPI scrape
  [Express]  GET  /onboarding/scrape-status/:jobId → poll scrape progress
  [FastAPI]  POST /ingest/company                  → direct scrape (unit test)
  [FastAPI]  GET  /knowledge/company/:tenantId     → chunk retrieval + metadata check
  [FastAPI]  DELETE /knowledge/:tenantId/:chunkId  → chunk deletion

Prerequisites
-------------
  docker-compose up  (starts Postgres, Redis, ChromaDB, MinIO)
  Start Express:  cd new_backend/express-backend && pnpm start
  Start FastAPI:  cd new_backend/ingestion-service && uvicorn main:app --reload --port 8001

Run:
  pip install httpx pytest pytest-asyncio
  pytest test_company_onboarding.py -v

Or smoke-test directly:
  python test_company_onboarding.py
"""

import sys, io
# Ensure UTF-8 output on Windows (avoids UnicodeEncodeError for emoji)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import asyncio
import time
import pytest
import httpx

EXPRESS_URL  = "http://localhost:8000"
FASTAPI_URL  = "http://localhost:8001"

# We use a unique tenant ID per run so tests don't pollute each other
TENANT_ID    = f"test-tenant-{int(time.time())}"
TEST_WEBSITE = "https://www.frcrce.ac.in"
COMPANY_NAME = "Fr. C. Rodrigues College of Engineering, Bandra Mumbai"

# A real Clerk JWT is required for the Express endpoints.
# Set CLERK_TEST_TOKEN to a valid JWT (dev / test mode) before running.
import os
CLERK_TOKEN = os.getenv("CLERK_TEST_TOKEN", "")


def express_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if CLERK_TOKEN:
        h["Authorization"] = f"Bearer {CLERK_TOKEN}"
    return h


async def poll_scrape_job(client: httpx.AsyncClient, job_id: str,
                          base_url: str, via_express: bool = False,
                          timeout_secs: int = 200) -> dict:
    """Poll job status until completed/failed or timeout."""
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        if via_express:
            r = await client.get(
                f"{base_url}/onboarding/scrape-status/{job_id}",
                headers=express_headers(),
                timeout=10,
            )
        else:
            r = await client.get(f"{base_url}/status/{job_id}", timeout=10)
        r.raise_for_status()
        data = r.json()
        status = data.get("status", "")
        if status == "completed":
            return data
        if isinstance(status, str) and status.startswith("failed"):
            pytest.fail(f"Scrape job failed: {status}")
        await asyncio.sleep(2)
    pytest.fail(f"Job did not complete within {timeout_secs}s — last status: {data}")


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI Direct Tests  (no auth required)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_fastapi_health():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{FASTAPI_URL}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"
    print("✅ FastAPI health OK")


@pytest.mark.asyncio
async def test_fastapi_company_scrape_and_metadata():
    """Full FastAPI pipeline: ingest → poll → verify metadata → delete."""
    async with httpx.AsyncClient() as c:

        # 1. Trigger scrape
        r = await c.post(f"{FASTAPI_URL}/ingest/company", json={
            "tenantId":    TENANT_ID,
            "website_url": TEST_WEBSITE,
            "company_name": COMPANY_NAME,
        }, timeout=30)
        assert r.status_code == 200
        job_id = r.json()["job_id"]
        assert job_id, "No job_id returned"
        print(f"  Job started: {job_id}")

        # 2. Poll until done
        final = await poll_scrape_job(c, job_id, FASTAPI_URL, timeout_secs=200)
        pages  = final.get("pages_scraped", 0)
        chunks = final.get("chunks_processed", 0)
        print(f"  Completed — pages={pages} chunks={chunks}")
        assert chunks > 0, "Scraping produced 0 chunks"

        # 3. Fetch knowledge and verify metadata
        r = await c.get(f"{FASTAPI_URL}/knowledge/company/{TENANT_ID}", timeout=15)
        assert r.status_code == 200
        kb_chunks = r.json().get("chunks", [])
        assert len(kb_chunks) > 0, "ChromaDB returned 0 chunks"

        for ch in kb_chunks:
            meta = ch.get("metadata", {})
            assert meta.get("source_type") == "company_profile",  f"Wrong source_type: {meta}"
            assert meta.get("tenantId")    == TENANT_ID,           f"Wrong tenantId: {meta}"
            assert meta.get("agentId")     == "company_profile",   f"Wrong agentId: {meta}"
            assert ch.get("content"),                               f"Empty content for {ch['id']}"
        print(f"  All {len(kb_chunks)} chunks have correct metadata ✅")

        # 4. Delete first chunk and confirm removal
        chunk_id = kb_chunks[0]["id"]
        r = await c.delete(f"{FASTAPI_URL}/knowledge/{TENANT_ID}/{chunk_id}", timeout=10)
        assert r.status_code == 200 and r.json()["deleted"] is True

        r = await c.get(f"{FASTAPI_URL}/knowledge/company/{TENANT_ID}", timeout=10)
        remaining = [c["id"] for c in r.json().get("chunks", [])]
        assert chunk_id not in remaining, "Deleted chunk still present!"
        print(f"  Chunk deletion confirmed ✅  ({len(remaining)} remaining)")


@pytest.mark.asyncio
async def test_fastapi_status_shape():
    """Status endpoint must return pages_scraped + chunks_processed fields."""
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{FASTAPI_URL}/ingest/company", json={
            "tenantId":    f"{TENANT_ID}-shape",
            "website_url": TEST_WEBSITE,
            "company_name": COMPANY_NAME,
        }, timeout=30)
        job_id = r.json()["job_id"]

        for _ in range(3):
            sr = await c.get(f"{FASTAPI_URL}/status/{job_id}", timeout=10)
            d = sr.json()
            assert "status"            in d, f"Missing status: {d}"
            assert "progress"          in d, f"Missing progress: {d}"
            assert "pages_scraped"     in d, f"Missing pages_scraped: {d}"
            assert "chunks_processed"  in d, f"Missing chunks_processed: {d}"
            await asyncio.sleep(2)
    print("✅ Status endpoint shape correct")


@pytest.mark.asyncio
async def test_fastapi_empty_for_unknown_tenant():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{FASTAPI_URL}/knowledge/company/no-such-tenant-xyz", timeout=10)
        assert r.status_code == 200
        assert r.json()["total"] == 0
    print("✅ Empty result for unknown tenant")


# ═══════════════════════════════════════════════════════════════════════════════
# Express Endpoint Tests  (requires CLERK_TEST_TOKEN or auth disabled)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_express_health():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{EXPRESS_URL}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
    print("✅ Express health OK")


@pytest.mark.asyncio
@pytest.mark.skipif(not CLERK_TOKEN, reason="CLERK_TEST_TOKEN not set — skipping Express auth tests")
async def test_express_company_search():
    """Company-search typeahead must return matching entries with expected fields."""
    async with httpx.AsyncClient() as c:

        # ── Query that should match well-known companies ──
        for query, expected_substring in [
            ("tata",     "Tata"),
            ("infosys",  "Infosys"),
            ("razorpay", "Razorpay"),
            ("google",   "Google"),
        ]:
            r = await c.get(
                f"{EXPRESS_URL}/onboarding/company-search",
                params={"q": query},
                headers=express_headers(),
                timeout=10,
            )
            assert r.status_code == 200, f"Non-200 for q={query}: {r.text}"
            companies = r.json().get("companies", [])
            assert len(companies) > 0, f"No results for query '{query}'"
            names = [c["name"] for c in companies]
            assert any(expected_substring in n for n in names), (
                f"Expected '{expected_substring}' in results for '{query}', got: {names}"
            )
            for co in companies:
                assert "id"       in co, f"Missing id: {co}"
                assert "name"     in co, f"Missing name: {co}"
                assert "domain"   in co, f"Missing domain: {co}"
                assert "industry" in co, f"Missing industry: {co}"

        # ── Empty query should return [] not an error ──
        r = await c.get(
            f"{EXPRESS_URL}/onboarding/company-search",
            params={"q": ""},
            headers=express_headers(),
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["companies"] == []

        print("✅ Express company-search endpoint working correctly")


@pytest.mark.asyncio
@pytest.mark.skipif(not CLERK_TOKEN, reason="CLERK_TEST_TOKEN not set — skipping Express auth tests")
async def test_express_save_company_triggers_scrape():
    """POST /onboarding/company must save & return a scrapeJobId."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{EXPRESS_URL}/onboarding/company",
            json={
                "company_name": COMPANY_NAME,
                "industry":     "technology",
                "use_case":     "customer-support",
                "website_url":  TEST_WEBSITE,
            },
            headers=express_headers(),
            timeout=30,
        )
        assert r.status_code == 200, f"Non-200: {r.text}"
        data = r.json()
        assert data.get("success") is True, f"success!=True: {data}"
        job_id = data.get("scrapeJobId")
        assert job_id, "No scrapeJobId returned — scrape was not triggered"
        print(f"✅ Express saved company; scrape job: {job_id}")

        # Poll via the Express proxy endpoint
        final = await poll_scrape_job(c, job_id, EXPRESS_URL, via_express=True)
        print(f"  Scrape done via Express proxy — pages={final.get('pages_scraped')}")


# ═══════════════════════════════════════════════════════════════════════════════
# Smoke test (run directly: python test_company_onboarding.py)
# ═══════════════════════════════════════════════════════════════════════════════

async def _smoke():
    print("\n=== Smoke test ===")
    async with httpx.AsyncClient() as c:

        print("1. FastAPI health…")
        r = await c.get(f"{FASTAPI_URL}/health", timeout=10)
        print(f"   {r.json()}")

        print("2. Trigger company scrape for example.com…")
        r = await c.post(f"{FASTAPI_URL}/ingest/company", json={
            "tenantId":    f"smoke-{int(time.time())}",
            "website_url": "https://example.com",
            "company_name": "Example",
        }, timeout=30)
        data = r.json()
        job_id = data["job_id"]
        print(f"   Job ID: {job_id}  status={data['status']}")

        print("3. Polling…")
        final = await poll_scrape_job(c, job_id, FASTAPI_URL)
        print(f"   Done! pages={final.get('pages_scraped')} chunks={final.get('chunks_processed')}")

        tid = f"smoke-{int(time.time())}"
        print(f"4. Fetching knowledge for tenant {tid}…")
        # re-run ingest so we have something to fetch
        r2 = await c.post(f"{FASTAPI_URL}/ingest/company", json={
            "tenantId": tid, "website_url": "https://example.com", "company_name": "Example"
        }, timeout=30)
        jid2 = r2.json()["job_id"]
        await poll_scrape_job(c, jid2, FASTAPI_URL, timeout_secs=90)
        r3 = await c.get(f"{FASTAPI_URL}/knowledge/company/{tid}", timeout=15)
        kb = r3.json()
        print(f"   Total chunks: {kb['total']}")
        if kb["chunks"]:
            ch0 = kb["chunks"][0]
            print(f"   First chunk source_type: {ch0['metadata'].get('source_type')}")
            print(f"   First chunk preview: {ch0['content'][:100]}…")

        print("\n✅ Smoke test passed")


if __name__ == "__main__":
    asyncio.run(_smoke())
