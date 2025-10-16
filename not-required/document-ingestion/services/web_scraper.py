"""
Web Scraping Service using Crawl4AI
Handles URL scraping with support for JavaScript, pagination, and dynamic content
"""

import asyncio
import os
import time
import math
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import logging
from typing import Optional, List, Dict, Any
import httpx
import re
from urllib.parse import urljoin, urlparse
import json
import hashlib
import sys
from datetime import datetime

try:
    import aiohttp
    _HAS_AIOHTTP = True
except Exception:
    _HAS_AIOHTTP = False

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
        # Rate limiting controls (requests per second) - default to 1 rps
        self.rate_limit_rps = float(os.environ.get('SCRAPER_RATE_LIMIT_RPS', '1.0'))
        # Respect robots.txt by default (toggle with env var)
        self.respect_robots = str(os.environ.get('SCRAPER_RESPECT_ROBOTS', 'true')).lower() in ("1", "true", "yes", "on")
        # Max retries and backoff
        self.max_retries = int(os.environ.get('SCRAPER_MAX_RETRIES', '3'))
        self.backoff_base = float(os.environ.get('SCRAPER_BACKOFF_BASE', '0.5'))
        # Optional proxy
        self.http_proxies = os.environ.get('SCRAPER_HTTP_PROXY')
        # Ingestion configuration (optional): embed + upsert to Chroma
        self.ingest_after_scrape = str(os.environ.get('SCRAPER_INGEST_AFTER_SCRAPE', 'false')).lower() in ("1", "true", "yes", "on")
        self.chroma_path = os.environ.get('CHROMA_DB_PATH', './chroma_db')
    
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
        logger.info(f"🔍 Starting web scraping process for URL: {url}")
        logger.info(f"📋 Scrape configuration: wait_for_js={wait_for_js}, respect_robots={self.respect_robots}")

        # robots.txt check
        if self.respect_robots and not await self._allowed_by_robots(url):
            logger.warning(f"🚫 Robots.txt disallows scraping URL: {url}")
            return ""

        # If configured to force HTTP-only fetching, skip the JS/Crawl4AI path
        if self.force_http or not wait_for_js:
            logger.info("🌐 Using HTTP-only fetch (no JavaScript rendering)")
            return await self._http_fetch(url)
        
        try:
            logger.info("⚙️ Configuring Crawl4AI crawler...")
            # Configure crawler run
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=self.md_generator,
                page_timeout=30000,  # 30 seconds timeout
                wait_for_images=False,  # Speed optimization
                screenshot=False,  # Don't need screenshots
                verbose=False
            )
            logger.info("✅ Crawler configuration complete")
            
            logger.info("🚀 Initializing AsyncWebCrawler...")
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                logger.info(f"📡 Fetching URL with crawler: {url}")
                
                result = await crawler.arun(url=url, config=run_config)
                logger.info(f"📊 Crawl result received: success={result.success}")
                
                if not result.success:
                    error_msg = result.error_message or "Unknown error"
                    logger.error(f"❌ Crawl failed: {error_msg}")
                    raise Exception(f"Failed to scrape URL: {error_msg}")
                
                # Get filtered markdown content
                content = result.markdown.fit_markdown or result.markdown.raw_markdown
                logger.info(f"📝 Content extracted: {len(content)} characters")
                logger.info(f"📄 Content preview: {content[:200]}...")
                
                # optional ingestion pipeline
                if self.ingest_after_scrape and content:
                    logger.info("💾 Ingesting scraped content...")
                    await self._ingest_scraped_content(url, content)
                    logger.info("✅ Content ingestion complete")
                
                logger.info("🎉 Web scraping process completed successfully")
                return content
        
        except Exception as e:
            logger.error(f"💥 Error in JavaScript scraping (Crawl4AI): {e}", exc_info=True)
            logger.info("🔄 Falling back to HTTP fetch...")
            # Fall back to HTTP fetch
            return await self._http_fetch(url)

    async def _http_fetch(self, url: str) -> str:
        """
        Simple HTTP fetch fallback that extracts text using BeautifulSoup when available.
        Returns empty string on any failure.
        """
        try:
            logger.info(f"🌐 Starting HTTP fallback fetch for URL: {url}")
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, proxies=self.http_proxies) as client:
                logger.info("📡 Sending HTTP GET request...")
                resp = await client.get(url)
                logger.info(f"📊 HTTP response received: status={resp.status_code}")
                resp.raise_for_status()
                html = resp.text or ""
                logger.info(f"📄 Raw HTML received: {len(html)} characters")

            if not html or len(html.strip()) == 0:
                logger.warning("⚠️ HTTP fallback returned empty body")
                return ""

            if _HAS_BS4:
                try:
                    logger.info("🍲 Processing HTML with BeautifulSoup...")
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(separator="\n")
                    logger.info(f"✅ BeautifulSoup extraction succeeded: {len(text)} characters")
                    logger.info(f"📝 Extracted text preview: {text[:200]}...")
                    
                    if self.ingest_after_scrape and text:
                        logger.info("💾 Ingesting BeautifulSoup content...")
                        await self._ingest_scraped_content(url, text)
                        logger.info("✅ BeautifulSoup content ingestion complete")
                    return text
                except Exception as be:
                    logger.warning(f"⚠️ BeautifulSoup extraction failed: {be}")
                    logger.info("🔄 Falling back to raw HTML...")
                    # Fall through to return raw HTML

            logger.info(f"✅ HTTP fallback succeeded (raw HTML): {len(html)} characters")
            if self.ingest_after_scrape and html:
                logger.info("💾 Ingesting raw HTML content...")
                await self._ingest_scraped_content(url, html)
                logger.info("✅ Raw HTML content ingestion complete")
            return html

        except Exception as hf:
            logger.error(f"💥 HTTP fallback failed: {hf}", exc_info=True)
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

        # robots.txt check
        if self.respect_robots and not await self._allowed_by_robots(url):
            logger.warning(f"Robots.txt disallows scraping URL: {url}")
            return ""
        
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
                # Improved pagination heuristics: try selectors, rel=next links, textual 'Next' links
                current_url = url
                for page_num in range(2, max_pages + 1):
                    # attempt selector click first
                    run_config_with_js = run_config.clone(js_code=[js_click_next])
                    result = await crawler.arun(url=current_url, config=run_config_with_js)
                    if not result.success:
                        logger.info(f"Pagination attempt (selector) failed at page {page_num}")
                    else:
                        content = result.markdown.fit_markdown or result.markdown.raw_markdown
                        # If content changed, accept and continue
                        if content and content not in all_content:
                            all_content.append(content)
                            logger.info(f"Page {page_num} scraped (selector): {len(content)} characters")
                            # attempt to detect new URL after click
                            new_url = self._detect_next_url_from_html(content, current_url)
                            if new_url and new_url != current_url:
                                current_url = new_url
                                continue
                            else:
                                continue

                    # If selector approach failed, try to follow rel=next or 'Next' link via HTTP fetch
                    http_html = await self._http_fetch(current_url)
                    if not http_html:
                        logger.info(f"No HTTP content to check for next link at page {page_num}")
                        break
                    next_link = self._find_next_link(http_html, current_url)
                    if not next_link:
                        logger.info(f"No next link found at page {page_num}; stopping pagination")
                        break
                    # follow next link
                    current_url = next_link
                    # fetch next page using crawler for JS sites
                    result = await crawler.arun(url=current_url, config=run_config)
                    if not result.success:
                        logger.info(f"Failed to fetch next page {page_num} at {current_url}")
                        break
                    content = result.markdown.fit_markdown or result.markdown.raw_markdown
                    if content and content not in all_content:
                        all_content.append(content)
                        logger.info(f"Page {page_num} scraped (follow link): {len(content)} characters")
                    else:
                        logger.info(f"No new content at page {page_num}, stopping")
                        break
            
            combined_content = "\n\n".join(all_content)
            logger.info(f"Paginated scrape complete: {len(combined_content)} total characters from {len(all_content)} pages")
            if self.ingest_after_scrape and combined_content:
                await self._ingest_scraped_content(url, combined_content)
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

    async def _allowed_by_robots(self, url: str) -> bool:
        """Check robots.txt for allowed user-agent '*'"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(robots_url)
                if r.status_code != 200:
                    return True
                txt = r.text or ''
                # Simple check: look for Disallow: / or Disallow: <path-prefix> matching our path
                path = parsed.path or '/'
                for line in txt.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if line.lower().startswith('user-agent:'):
                        ua = line.split(':', 1)[1].strip()
                        # we're only honoring '*' entries for simplicity
                        continue
                    if line.lower().startswith('disallow:'):
                        value = line.split(':', 1)[1].strip()
                        if value == '/' or (value and path.startswith(value)):
                            return False
                return True
        except Exception:
            return True

    def _find_next_link(self, html: str, base_url: str) -> Optional[str]:
        """Find likely next-page link from HTML using common patterns"""
        try:
            # quick regex search for rel="next"
            m = re.search(r"<a[^>]+rel=[\"']?next[\"']?[^>]*href=[\"']([^\"']+)[\"']", html, re.IGNORECASE)
            if m:
                return urljoin(base_url, m.group(1))
            # look for text-based next links
            m2 = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(?:\s*Next|\s*Next\s*›|\s*»|\s*Next page|\s*Page\s*2)\s*</a>", html, re.IGNORECASE)
            if m2:
                return urljoin(base_url, m2.group(1))
            # generic href with 'page=' or '/page/' patterns
            m3 = re.search(r"href=[\"']([^\"']*(?:page=|/page/)[^\"']*)[\"']", html, re.IGNORECASE)
            if m3:
                return urljoin(base_url, m3.group(1))
            return None
        except Exception:
            return None

    def _detect_next_url_from_html(self, html: str, current_url: str) -> Optional[str]:
        """Attempt to detect if HTML indicates a URL change after an in-page click"""
        # Very heuristic: search for window.location or fetch/XHR calls
        try:
            m = re.search(r"window\.location\s*=\s*[\"']([^\"']+)[\"']", html)
            if m:
                return urljoin(current_url, m.group(1))
            return None
        except Exception:
            return None

    async def _ingest_scraped_content(self, source_url: str, content: str):
        """Chunk content, embed and upsert to ChromaDB if an embedder is available."""
        try:
            # lazy import of embedder and chroma client to avoid heavy deps for scraper-only runs
            ingestion_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
            if ingestion_path not in sys.path:
                sys.path.insert(0, ingestion_path)
            from services.embedder import TextEmbedder
            import chromadb
            from chromadb.config import Settings

            embedder = TextEmbedder()  # use default model
            client = chromadb.PersistentClient(path=self.chroma_path, settings=Settings(anonymized_telemetry=False))
            collection = client.get_or_create_collection(name=os.environ.get('COLLECTION_NAME', 'documents'))

            # chunk content into ~1-2KB chunks with 200-char overlap
            chunk_size = int(os.environ.get('INGEST_CHUNK_SIZE', '1500'))
            overlap = int(os.environ.get('INGEST_CHUNK_OVERLAP', '200'))
            cleaned = content.strip()
            chunks = []
            i = 0
            while i < len(cleaned):
                chunk = cleaned[i:i+chunk_size]
                chunks.append(chunk)
                i += chunk_size - overlap

            # embed in batches
            embeddings = []
            batch = []
            batch_texts = []
            for text in chunks:
                batch_texts.append(text)
                if len(batch_texts) >= 16:
                    emb_batch = embedder.model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=False)
                    embeddings.extend([list(e) for e in emb_batch])
                    batch_texts = []
            if batch_texts:
                emb_batch = embedder.model.encode(batch_texts, show_progress_bar=False, convert_to_numpy=False)
                embeddings.extend([list(e) for e in emb_batch])

            # upsert
            ids = [f"scrape::{hashlib.sha256((source_url + str(i)).encode()).hexdigest()}" for i in range(len(chunks))]
            metadatas = [{'source': source_url, 'chunk_index': idx, 'doc_type': 'scrape', 'crawl_date': datetime.utcnow().isoformat()} for idx in range(len(chunks))]
            collection.add(documents=chunks, metadatas=metadatas, ids=ids, embeddings=embeddings)
            logger.info(f"Ingested {len(chunks)} chunks from {source_url} into ChromaDB")
            # write an ingestion manifest for auditing and potential resume
            try:
                manifest_dir = os.path.join(self.chroma_path, 'ingestion_manifests')
                os.makedirs(manifest_dir, exist_ok=True)
                manifest = {
                    'source_url': source_url,
                    'timestamp': datetime.utcnow().isoformat(),
                    'num_chunks': len(chunks),
                    'ids': ids,
                    'metadatas_sample': metadatas[:3]
                }
                manifest_path = os.path.join(manifest_dir, f"ingest_{hashlib.sha256(source_url.encode()).hexdigest()[:8]}_{int(time.time())}.json")
                with open(manifest_path, 'w', encoding='utf-8') as mf:
                    json.dump(manifest, mf, ensure_ascii=False, indent=2)
                logger.info(f"Ingestion manifest written: {manifest_path}")
            except Exception:
                logger.exception('Failed to write ingestion manifest')
        except Exception:
            logger.exception('Ingestion of scraped content failed')