import asyncio
from crawl4ai import AsyncWebCrawler

async def test_scraping():
    urls = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://www.python.org/",
        "https://news.ycombinator.com/"
    ]

    async with AsyncWebCrawler() as crawler:
        for url in urls:
            print(f"Scraping {url}...")
            try:
                result = await crawler.arun(url=url)
                if result and result.markdown:
                    print(f"Success: Got {len(result.markdown)} characters")
                    print(f"Preview: {result.markdown[:200]}...")
                else:
                    print("Failed: No content")
            except Exception as e:
                print(f"Error: {e}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_scraping())