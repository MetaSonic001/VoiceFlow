"""
Web Scraping Service using Crawl4AI
Handles URL scraping with support for JavaScript, pagination, and dynamic content
"""

import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import logging
from typing import Optional
import httpx

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    _HAS_BS4 = False

logger = logging.getLogger(__name__)


class WebScraper:
    """
    Service for web scraping using Crawl4AI
    Supports static HTML, JavaScript-rendered content, and paginated websites
    """
    
    def __init__(self):
        self.browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True,
            verbose=False
        )
        
        # Configure markdown generator with content filtering
        self.md_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.4,
                threshold_type="fixed"
            )
        )
        
        logger.info("WebScraper initialized with Crawl4AI")
        # Allow forcing simple HTTP fetching (no JS rendering) via env var.
        force_http = os.environ.get("WEB_SCRAPER_FORCE_HTTP", os.environ.get("FORCE_HTTP_SCRAPER", "false"))
        self.force_http = str(force_http).lower() in ("1", "true", "yes", "on")
        if self.force_http:
            logger.info("WebScraper configured to force HTTP-only fetching (no JS rendering)")
    
    def is_available(self) -> bool:
        """Check if scraper service is available"""
        return True
    
    async def scrape(self, url: str, wait_for_js: bool = True) -> str:
        """
        Scrape a URL and extract text content
        
        Args:
            url: URL to scrape
            wait_for_js: Whether to wait for JavaScript rendering
        
        Returns:
            Extracted text content
        """
        logger.info(f"Starting scrape for URL: {url}")

        # If configured to force HTTP-only fetching, skip the JS/Crawl4AI path
        if self.force_http or not wait_for_js:
            logger.info("Using HTTP-only fetch (no JS) for URL")
            return await self._http_fetch(url)
        
        try:
            # Configure crawler run
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=self.md_generator,
                page_timeout=30000,  # 30 seconds timeout
                wait_for_images=False,  # Speed optimization
                screenshot=False,  # Don't need screenshots
                verbose=False
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                logger.info(f"Crawler initialized, fetching URL: {url}")
                
                result = await crawler.arun(url=url, config=run_config)
                
                if not result.success:
                    error_msg = result.error_message or "Unknown error"
                    logger.error(f"Crawl failed: {error_msg}")
                    raise Exception(f"Failed to scrape URL: {error_msg}")
                
                # Get filtered markdown content
                content = result.markdown.fit_markdown or result.markdown.raw_markdown
                
                logger.info(f"JS wait scrape complete: {len(content)} characters")
                return content
        
        except Exception as e:
            logger.error(f"Error in JS wait scraping (playwright/crawl4ai): {e}", exc_info=True)
            # Fall back to HTTP fetch
            return await self._http_fetch(url)

    async def _http_fetch(self, url: str) -> str:
        """
        Simple HTTP fetch fallback that extracts text using BeautifulSoup when available.
        Returns empty string on any failure.
        """
        try:
            logger.info("Attempting HTTP fallback fetch for URL")
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text or ""

            if not html or len(html.strip()) == 0:
                logger.warning("HTTP fallback returned empty body")
                return ""

            if _HAS_BS4:
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(separator="\n")
                    logger.info(f"HTTP fallback succeeded (BeautifulSoup): {len(text)} characters")
                    return text
                except Exception as be:
                    logger.warning(f"BeautifulSoup extraction failed: {be}")
                    # Fall through to return raw HTML

            logger.info(f"HTTP fallback succeeded (raw HTML): {len(html)} characters")
            return html

        except Exception as hf:
            logger.error(f"HTTP fallback also failed: {hf}", exc_info=True)
            return ""
    
    async def scrape_with_pagination(
        self,
        url: str,
        next_button_selector: str = "button.next",
        max_pages: int = 10
    ) -> str:
        """
        Scrape a paginated website
        
        Args:
            url: Starting URL
            next_button_selector: CSS selector for next page button
            max_pages: Maximum number of pages to scrape
        
        Returns:
            Combined text from all pages
        """
        logger.info(f"Starting paginated scrape for URL: {url}")
        
        try:
            all_content = []
            
            # JavaScript to click next button and wait
            js_click_next = f"""
            (async () => {{
                const nextBtn = document.querySelector('{next_button_selector}');
                if (nextBtn) {{
                    nextBtn.scrollIntoView();
                    nextBtn.click();
                    await new Promise(r => setTimeout(r, 2000));  // Wait 2 seconds
                    return true;
                }}
                return false;
            }})();
            """
            
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=self.md_generator,
                page_timeout=30000,
                verbose=False
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                # First page
                result = await crawler.arun(url=url, config=run_config)
                
                if result.success:
                    content = result.markdown.fit_markdown or result.markdown.raw_markdown
                    all_content.append(content)
                    logger.info(f"Page 1 scraped: {len(content)} characters")
                
                # Subsequent pages
                for page_num in range(2, max_pages + 1):
                    run_config_with_js = run_config.clone(js_code=[js_click_next])
                    
                    result = await crawler.arun(url=url, config=run_config_with_js)
                    
                    if not result.success:
                        logger.info(f"Pagination ended at page {page_num}")
                        break
                    
                    content = result.markdown.fit_markdown or result.markdown.raw_markdown
                    
                    # Check if content is different from previous page
                    if content and content not in all_content:
                        all_content.append(content)
                        logger.info(f"Page {page_num} scraped: {len(content)} characters")
                    else:
                        logger.info(f"No new content at page {page_num}, stopping")
                        break
            
            combined_content = "\n\n".join(all_content)
            logger.info(f"Paginated scrape complete: {len(combined_content)} total characters from {len(all_content)} pages")
            
            return combined_content
        
        except Exception as e:
            logger.error(f"Error in paginated scraping: {e}", exc_info=True)
            raise
    
    async def scrape_with_js_wait(
        self,
        url: str,
        wait_for_selector: str = None,
        js_code: str = None,
        wait_time: int = 3000
    ) -> str:
        """
        Scrape with custom JavaScript execution and waiting
        
        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for
            js_code: Custom JavaScript to execute
            wait_time: Time to wait in milliseconds
        
        Returns:
            Extracted text content
        """
        logger.info(f"Scraping with JS wait for URL: {url}")
        
        try:
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=self.md_generator,
                page_timeout=60000,
                wait_for=wait_for_selector,
                js_code=[js_code] if js_code else None,
                delay_before_return_html=wait_time,
                verbose=False
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                if not result.success:
                    raise Exception(f"Failed to scrape: {result.error_message}")
                
                content = result.markdown.fit_markdown or result.markdown.raw_markdown
        except Exception as e:
            logger.error(f"Error in scrape_with_js_wait: {e}", exc_info=True)
            raise