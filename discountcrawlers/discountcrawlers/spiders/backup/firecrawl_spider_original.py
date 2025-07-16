"""
Firecrawl Spider for Discount Crawlers
=====================================

This spider uses Firecrawl API for enhanced web scraping with JavaScript rendering,
structured data extraction, and advanced parsing capabilities.

Features:
- JavaScript rendering and waiting
- Structured data extraction
- Screenshot capture (optional)
- Rate limiting and retry logic
- Integration with existing Scrapy pipeline
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

import scrapy
from scrapy import signals
from scrapy.http import Request, Response
from scrapy.spiders import Spider

from ..firecrawl_integration import (
    FirecrawlConfig, 
    FirecrawlClient, 
    FirecrawlRequest,
    FirecrawlDiscountExtractor
)
from ..items import DiscountItem

LOGGER = logging.getLogger(__name__)

class FirecrawlSpider(Spider):
    """Spider that uses Firecrawl API for enhanced web scraping."""
    
    name = 'firecrawl'
    custom_settings = {
        'DOWNLOAD_DELAY': 2,  # Respect rate limits
        'CONCURRENT_REQUESTS': 3,  # Reduced for API limits
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'AUTOTHROTTLE_DEBUG': True,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load Firecrawl configuration
        self.firecrawl_config = self._load_firecrawl_config()
        self.firecrawl_client = None
        self.extractor = None
        
        # Spider state
        self.stats = {
            'requests_made': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'rate_limited': 0,
        }
    
    def _load_firecrawl_config(self) -> FirecrawlConfig:
        """Load Firecrawl configuration from environment."""
        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable is required")
        
        return FirecrawlConfig(
            api_key=api_key,
            timeout=int(os.getenv('FIRECRAWL_TIMEOUT', '30')),
            max_retries=int(os.getenv('FIRECRAWL_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('FIRECRAWL_RETRY_DELAY', '1.0')),
            max_concurrent_requests=int(os.getenv('FIRECRAWL_MAX_CONCURRENT', '5')),
            enable_screenshots=os.getenv('FIRECRAWL_ENABLE_SCREENSHOTS', 'false').lower() == 'true',
            enable_pdf=os.getenv('FIRECRAWL_ENABLE_PDF', 'false').lower() == 'true',
            wait_for_timeout=int(os.getenv('FIRECRAWL_WAIT_TIMEOUT', '5000')),
        )
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Initialize spider with crawler."""
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider
    
    def spider_opened(self, spider):
        """Called when spider opens."""
        LOGGER.info(f"Firecrawl spider opened: {spider.name}")
        
        # Initialize Firecrawl client
        self.firecrawl_client = FirecrawlClient(self.firecrawl_config)
        self.extractor = FirecrawlDiscountExtractor(self.firecrawl_client)
    
    def spider_closed(self, spider):
        """Called when spider closes."""
        LOGGER.info(f"Firecrawl spider closed: {spider.name}")
        LOGGER.info(f"Stats: {self.stats}")
        
        # Clean up Firecrawl client
        if self.firecrawl_client and hasattr(self.firecrawl_client, 'session'):
            asyncio.create_task(self.firecrawl_client.session.close())
    
    def start_requests(self):
        """Generate initial requests."""
        # Example URLs for testing - replace with your actual URLs
        test_urls = [
            "https://httpbin.org/html",  # Simple test page
            "https://httpbin.org/forms/post",  # Form page
        ]
        
        for url in test_urls:
            yield Request(
                url=url,
                callback=self.parse_with_firecrawl,
                meta={'store_name': 'test_store'}
            )
    
    def parse_with_firecrawl(self, response: Response):
        """Parse response using Firecrawl API."""
        url = response.url
        store_name = response.meta.get('store_name', 'unknown')
        
        LOGGER.info(f"Processing URL with Firecrawl: {url}")
        self.stats['requests_made'] += 1
        
        # Create async task for Firecrawl processing
        return asyncio.create_task(self._process_with_firecrawl(url, store_name))
    
    async def _process_with_firecrawl(self, url: str, store_name: str):
        """Process URL using Firecrawl API."""
        try:
            async with self.firecrawl_client:
                # Extract discount data
                item = await self.extractor.extract_discount_data(url, store_name)
                
                if item:
                    self.stats['successful_extractions'] += 1
                    LOGGER.info(f"Successfully extracted data from {url}")
                    yield item
                else:
                    self.stats['failed_extractions'] += 1
                    LOGGER.warning(f"Failed to extract data from {url}")
                    
        except Exception as e:
            self.stats['failed_extractions'] += 1
            LOGGER.error(f"Error processing {url} with Firecrawl: {e}")
    
    def parse(self, response: Response):
        """Default parse method - not used in this spider."""
        pass

class FirecrawlProductSpider(FirecrawlSpider):
    """Spider for extracting product information using Firecrawl."""
    
    name = 'firecrawl_products'
    
    def start_requests(self):
        """Generate requests for product pages."""
        # Example product URLs - replace with actual URLs
        product_urls = [
            "https://httpbin.org/html",  # Test page
        ]
        
        for url in product_urls:
            yield Request(
                url=url,
                callback=self.parse_product,
                meta={'store_name': 'test_store'}
            )
    
    async def parse_product(self, response: Response):
        """Parse product page using Firecrawl."""
        url = response.url
        store_name = response.meta.get('store_name', 'unknown')
        
        LOGGER.info(f"Processing product page: {url}")
        
        try:
            async with self.firecrawl_client:
                # Create a more detailed extraction request
                request = FirecrawlRequest(
                    url=url,
                    formats=["markdown", "html"],
                    actions=[
                        {"type": "wait", "milliseconds": 3000},
                        {"type": "scrape"}
                    ],
                    wait_for_selectors=[".product-title", ".price", ".product-price"],
                    wait_for_timeout=5000,
                    only_main_content=True,
                    metadata={
                        "store": store_name,
                        "extracted_at": datetime.utcnow().isoformat(),
                        "spider": self.name
                    }
                )
                
                result = await self.firecrawl_client.scrape_url(request)
                
                if result.get("success"):
                    data = result.get("data", {})
                    markdown_content = data.get("markdown", "")
                    html_content = data.get("html", "")
                    
                    # Create item with extracted data
                    item = DiscountItem()
                    item['url'] = url
                    item['source'] = store_name
                    item['name'] = self._extract_title(markdown_content)
                    item['description'] = self._extract_description(markdown_content)
                    item['price'] = self._extract_price(markdown_content)
                    item['image_urls'] = self._extract_images(html_content)
                    item['crawled_at'] = datetime.utcnow().isoformat()
                    
                    self.stats['successful_extractions'] += 1
                    yield item
                else:
                    self.stats['failed_extractions'] += 1
                    LOGGER.error(f"Firecrawl extraction failed: {result.get('error')}")
                    
        except Exception as e:
            self.stats['failed_extractions'] += 1
            LOGGER.error(f"Error processing product {url}: {e}")
    
    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content."""
        import re
        match = re.search(r'#\s*(.+?)(?:\n|$)', content)
        return match.group(1).strip() if match else ""
    
    def _extract_description(self, content: str) -> str:
        """Extract description from markdown content."""
        import re
        # Look for paragraphs after the title
        paragraphs = re.findall(r'\n\n(.+?)(?:\n\n|\n#|$)', content, re.DOTALL)
        return paragraphs[0].strip() if paragraphs else ""
    
    def _extract_price(self, content: str) -> Optional[float]:
        """Extract price from markdown content."""
        import re
        match = re.search(r'\$?([\d,]+\.?\d*)', content)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass
        return None
    
    def _extract_images(self, html_content: str) -> List[str]:
        """Extract image URLs from HTML content."""
        import re
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, html_content)
        return matches[:5]  # Limit to 5 images 