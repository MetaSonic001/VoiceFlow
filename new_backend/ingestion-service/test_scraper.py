"""
Scraper test / preview tool
============================
Lets you quickly test all four scraper strategies against any URL,
directly importing from main.py — no FastAPI server needed.

Usage
-----
  # From inside new_backend/ingestion-service:
  python test_scraper.py https://example.com
  python test_scraper.py https://example.com --strategy playwright
  python test_scraper.py https://example.com --strategy trafilatura
  python test_scraper.py https://example.com --strategy requests
  python test_scraper.py https://example.com --all          # run all 4 and compare

Options
-------
  URL            required — the page to scrape
  --strategy     auto | trafilatura | playwright | requests  (default: auto)
  --all          run all 4 strategies side-by-side and show a comparison table
  --chars N      show first N characters of output (default: 600)
  --company      also run _process_company_sync (scrapes the whole domain)
                 requires --tenant (e.g. --tenant test-tenant-001)
  --tenant ID    tenant id to use when running --company mode

Examples
--------
  python test_scraper.py https://www.frcrce.ac.in --all
  python test_scraper.py https://stripe.com --strategy playwright --chars 1000
  python test_scraper.py https://docs.stripe.com --company --tenant mytenant

Notes
-----
  • Playwright requires chromium to be installed:
      python -m playwright install chromium
  • Run from the ingestion-service directory so imports resolve correctly.
"""

import sys
import time
import argparse
import importlib
import traceback
from typing import Optional

# ── make sure we can import from main.py -----------------------------------
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Patch environment so main.py doesn't crash on missing infra
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("CHROMA_HOST", "localhost")
os.environ.setdefault("CHROMA_PORT", "8002")
os.environ.setdefault("MINIO_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")

# We only need the scraper functions — suppress startup noise
print("Loading scraper module (may take ~10s for embedding model)…", flush=True)
try:
    from main import _scrape_url_sync, _scrape_with_playwright
    _scrape_url_sync_available = True
except ImportError as e:
    print(f"ERROR: Could not import from main.py — {e}")
    print("Make sure you run this from the ingestion-service directory.")
    sys.exit(1)
except Exception as e:
    # Redis / ChromaDB not running is fine for a scrape-only test
    print(f"Note: infra not running ({e}) — scraper functions still available")
    # Try a targeted import
    _scrape_url_sync_available = False


STRATEGIES = ["auto", "trafilatura", "requests", "playwright"]


def scrape(url: str, strategy: str, chars: int) -> dict:
    t0 = time.perf_counter()
    content: Optional[str] = None
    error: Optional[str] = None
    try:
        content = _scrape_url_sync(url, strategy=strategy)
    except Exception as e:
        error = str(e)
    elapsed = time.perf_counter() - t0
    return {
        "strategy": strategy,
        "elapsed": elapsed,
        "chars": len(content) if content else 0,
        "content": content,
        "error": error,
        "preview": (content[:chars] if content else "(empty)"),
    }


def print_result(r: dict, chars: int):
    bar = "─" * 60
    status = f"{r['chars']:,} chars in {r['elapsed']:.2f}s"
    if r["error"]:
        status += f"  ERROR: {r['error']}"
    print(f"\n{bar}")
    print(f"  Strategy : {r['strategy'].upper()}")
    print(f"  Result   : {status}")
    print(bar)
    if r["content"]:
        print(r["preview"])
        if r["chars"] > chars:
            print(f"\n  … [{r['chars'] - chars:,} more chars not shown]")
    else:
        print("  (no content extracted)")


def print_comparison(results: list):
    print("\n" + "═" * 60)
    print("  STRATEGY COMPARISON")
    print("═" * 60)
    print(f"  {'Strategy':<15} {'Chars':>8}  {'Time':>7}  {'Status'}")
    print("  " + "─" * 50)
    for r in results:
        chars_str = f"{r['chars']:,}" if r["chars"] else "—"
        time_str = f"{r['elapsed']:.2f}s"
        status = "OK" if r["content"] else ("ERROR" if r["error"] else "empty")
        print(f"  {r['strategy']:<15} {chars_str:>8}  {time_str:>7}  {status}")
    print("═" * 60)
    best = max(results, key=lambda x: x["chars"])
    if best["chars"] > 0:
        print(f"  Best: {best['strategy'].upper()} ({best['chars']:,} chars)")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Test the VoiceFlow scraper against any URL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES,
        default="auto",
        help="Scraper strategy to use (default: auto)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all 4 strategies and show comparison table",
    )
    parser.add_argument(
        "--chars",
        type=int,
        default=600,
        help="How many characters of output to preview (default: 600)",
    )
    parser.add_argument(
        "--company",
        action="store_true",
        help="Run full company scrape (_process_company_sync) — crawls whole domain",
    )
    parser.add_argument(
        "--tenant",
        default="test-scraper-preview",
        help="Tenant ID to use for --company mode",
    )
    args = parser.parse_args()

    url = args.url
    if not url.startswith("http"):
        url = "https://" + url

    print(f"\nTarget URL : {url}")

    if args.all:
        print("Running all strategies…\n")
        results = []
        for strat in STRATEGIES:
            print(f"  [{strat}] scraping…", end=" ", flush=True)
            r = scrape(url, strat, args.chars)
            print(f"{r['chars']:,} chars ({r['elapsed']:.2f}s)")
            results.append(r)
        # show full preview for the best
        best = max(results, key=lambda x: x["chars"])
        print_result(best, args.chars)
        print_comparison(results)

    elif args.company:
        print(f"\nRunning full company scrape for tenant={args.tenant}")
        print("This may take 2-5 minutes (scrapes homepage + sub-pages)…\n")
        try:
            from main import _process_company_sync
        except ImportError:
            print("ERROR: Could not import _process_company_sync from main.py")
            sys.exit(1)

        import uuid as _uuid
        job_id = str(_uuid.uuid4())
        company_name = url.split("//")[-1].split("/")[0]

        t0 = time.perf_counter()
        try:
            _process_company_sync(
                job_id=job_id,
                tenant_id=args.tenant,
                website_url=url,
                company_name=company_name,
                additional_urls=[],
                strategy=args.strategy,
            )
            elapsed = time.perf_counter() - t0
            print(f"\n✓ Company scrape completed in {elapsed:.1f}s")
            print(f"  job_id   : {job_id}")
            print(f"  tenant   : {args.tenant}")
            print(f"  Check ChromaDB collection: tenant_{args.tenant}")
        except Exception as e:
            elapsed = time.perf_counter() - t0
            print(f"\n✗ Company scrape failed after {elapsed:.1f}s: {e}")
            traceback.print_exc()

    else:
        print(f"Strategy   : {args.strategy}")
        print("Scraping…\n")
        r = scrape(url, args.strategy, args.chars)
        print_result(r, args.chars)
        if not r["content"]:
            print("\nTip: try --strategy playwright for JS-heavy sites, or --all to compare.")


if __name__ == "__main__":
    main()
