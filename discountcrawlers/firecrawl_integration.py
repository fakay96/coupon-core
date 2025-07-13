"""
Firecrawl Integration for Discount Crawlers
==========================================

This module provides integration with Firecrawl API for enhanced web scraping
with structured data extraction, JavaScript rendering, and advanced parsing
capabilities.

Features:
- Structured data extraction with schemas
- JavaScript rendering and waiting
- Screenshot capture
- PDF generation
- Custom extraction rules
- Rate limiting and retry logic
- Integration with existing Scrapy pipeline
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
import requests
from urllib.parse import urlparse
from discountcrawlers.items import DiscountItem

LOGGER = logging.getLogger(__name__)

@dataclass
class FirecrawlConfig:
    """Configuration for Firecrawl API integration."""
    api_key: str
    base_url: str = "https://api.firecrawl.dev"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_concurrent_requests: int = 10
    enable_screenshots: bool = False
    enable_pdf: bool = False
    wait_for_selectors: Optional[List[str]] = None
    wait_for_timeout: int = 5000
    extract_rules: Optional[Dict[str, Any]] = None

@dataclass
class FirecrawlRequest:
    """Request configuration for Firecrawl API."""
    url: str
    extract_rules: Optional[Dict[str, Any]] = None
    wait_for_selectors: Optional[List[str]] = None
    wait_for_timeout: int = 5000
    screenshot: bool = False
    pdf: bool = False
    metadata: Optional[Dict[str, Any]] = None

class FirecrawlClient:
    """Client for interacting with Firecrawl API."""
    
    def __init__(self, config: FirecrawlConfig):
        self.config = config
        self.session = None
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_url(self, request: FirecrawlRequest) -> Dict[str, Any]:
        """Scrape a URL using Firecrawl API."""
        async with self._semaphore:
            payload = {
                "url": request.url,
                "waitForSelectors": request.wait_for_selectors or self.config.wait_for_selectors,
                "waitForTimeout": request.wait_for_timeout,
                "screenshot": request.screenshot or self.config.enable_screenshots,
                "pdf": request.pdf or self.config.enable_pdf,
                "metadata": request.metadata or {}
            }
            
            if request.extract_rules or self.config.extract_rules:
                payload["extractRules"] = request.extract_rules or self.config.extract_rules
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.post(
                        f"{self.config.base_url}/scrape",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            # Rate limited, wait and retry
                            wait_time = (2 ** attempt) * self.config.retry_delay
                            LOGGER.warning(f"Rate limited, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                            
                except Exception as e:
                    LOGGER.error(f"Firecrawl request failed (attempt {attempt + 1}): {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
            
            raise Exception("Max retries exceeded")

class FirecrawlDiscountExtractor:
    """Extractor for discount information using Firecrawl."""
    
    def __init__(self, client: FirecrawlClient):
        self.client = client
        
        # Common extraction rules for discount sites
        self.discount_extraction_rules = {
            "product": {
                "selector": "h1, .product-title, .product-name, [data-testid='product-title']",
                "type": "text"
            },
            "price": {
                "selector": ".price, .product-price, [data-testid='price'], .current-price",
                "type": "text"
            },
            "original_price": {
                "selector": ".original-price, .old-price, .was-price, [data-testid='original-price']",
                "type": "text"
            },
            "discount_percentage": {
                "selector": ".discount, .discount-percentage, .sale-badge, [data-testid='discount']",
                "type": "text"
            },
            "brand": {
                "selector": ".brand, .product-brand, [data-testid='brand']",
                "type": "text"
            },
            "description": {
                "selector": ".description, .product-description, [data-testid='description']",
                "type": "text"
            },
            "images": {
                "selector": "img[src*='product'], .product-image img, [data-testid='product-image']",
                "type": "attribute",
                "attribute": "src"
            },
            "availability": {
                "selector": ".stock, .availability, [data-testid='availability']",
                "type": "text"
            }
        }
    
    async def extract_discount_data(self, url: str, store_name: str) -> Optional[DiscountItem]:
        """Extract discount data from a URL using Firecrawl."""
        try:
            request = FirecrawlRequest(
                url=url,
                extract_rules=self.discount_extraction_rules,
                wait_for_selectors=[".product-title", ".price", ".product-price"],
                wait_for_timeout=5000,
                metadata={"store": store_name, "extracted_at": datetime.utcnow().isoformat()}
            )
            
            result = await self.client.scrape_url(request)
            
            if not result.get("success"):
                LOGGER.error(f"Firecrawl extraction failed for {url}: {result.get('error')}")
                return None
            
            data = result.get("data", {})
            extracted = data.get("extracted", {})
            
            # Create DiscountItem from extracted data
            item = DiscountItem()
            item['url'] = url
            item['source'] = store_name
            item['name'] = extracted.get('product', '')
            item['title'] = extracted.get('product', '')
            item['description'] = extracted.get('description', '')
            item['brand'] = extracted.get('brand', '')
            item['price'] = self._clean_price(extracted.get('price', ''))
            item['original_price'] = self._clean_price(extracted.get('original_price', ''))
            item['discount_percentage'] = self._extract_discount_percentage(extracted.get('discount_percentage', ''))
            item['stock_info'] = extracted.get('availability', '')
            item['image_urls'] = extracted.get('images', [])
            item['crawled_at'] = datetime.utcnow().isoformat()
            
            # Calculate discount percentage if not provided
            if not item['discount_percentage'] and item['price'] and item['original_price']:
                try:
                    original = float(item['original_price'])
                    current = float(item['price'])
                    if original > current:
                        item['discount_percentage'] = round(((original - current) / original) * 100, 2)
                except (ValueError, ZeroDivisionError):
                    pass
            
            return item
            
        except Exception as e:
            LOGGER.error(f"Error extracting discount data from {url}: {e}")
            return None
    
    def _clean_price(self, price_str: str) -> Optional[float]:
        """Clean and convert price string to float."""
        if not price_str:
            return None
        
        # Remove currency symbols and non-numeric characters except decimal point
        import re
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        
        # Handle different decimal separators
        if ',' in cleaned and '.' in cleaned:
            # European format: 1.234,56 -> 1234.56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned:
            # Check if comma is decimal separator
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _extract_discount_percentage(self, discount_str: str) -> Optional[float]:
        """Extract discount percentage from string."""
        if not discount_str:
            return None
        
        import re
        # Look for percentage patterns
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', discount_str)
        if match:
            return float(match.group(1))
        
        # Look for "save X" patterns
        match = re.search(r'save\s+(\d+(?:\.\d+)?)\s*%', discount_str.lower())
        if match:
            return float(match.group(1))
        
        return None

class FirecrawlSpiderMixin:
    """Mixin to add Firecrawl capabilities to Scrapy spiders."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firecrawl_client = None
        self.firecrawl_extractor = None
        
    async def setup_firecrawl(self, api_key: str):
        """Setup Firecrawl client and extractor."""
        config = FirecrawlConfig(
            api_key=api_key,
            wait_for_selectors=[".product-title", ".price", ".product-price"],
            enable_screenshots=False,
            enable_pdf=False
        )
        
        self.firecrawl_client = FirecrawlClient(config)
        self.firecrawl_extractor = FirecrawlDiscountExtractor(self.firecrawl_client)
    
    async def extract_with_firecrawl(self, url: str, store_name: str) -> Optional[DiscountItem]:
        """Extract discount data using Firecrawl."""
        if not self.firecrawl_extractor:
            raise RuntimeError("Firecrawl not initialized. Call setup_firecrawl() first.")
        
        return await self.firecrawl_extractor.extract_discount_data(url, store_name)

# Example usage in a spider
class FirecrawlDiscountSpider:
    """Example spider using Firecrawl for enhanced extraction."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.extractor = None
    
    async def setup(self):
        """Setup Firecrawl client."""
        config = FirecrawlConfig(
            api_key=self.api_key,
            wait_for_selectors=[".product-title", ".price"],
            extract_rules={
                "product": {"selector": "h1", "type": "text"},
                "price": {"selector": ".price", "type": "text"},
                "original_price": {"selector": ".original-price", "type": "text"}
            }
        )
        
        self.client = FirecrawlClient(config)
        self.extractor = FirecrawlDiscountExtractor(self.client)
    
    async def crawl_discounts(self, urls: List[str], store_name: str) -> List[DiscountItem]:
        """Crawl multiple URLs for discount data."""
        async with self.client:
            tasks = []
            for url in urls:
                task = self.extractor.extract_discount_data(url, store_name)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            items = []
            for result in results:
                if isinstance(result, DiscountItem):
                    items.append(result)
                elif isinstance(result, Exception):
                    LOGGER.error(f"Error during extraction: {result}")
            
            return items

# Utility functions
def create_firecrawl_config(api_key: str, **kwargs) -> FirecrawlConfig:
    """Create Firecrawl configuration with defaults."""
    return FirecrawlConfig(
        api_key=api_key,
        **kwargs
    )

def get_store_specific_rules(store_name: str) -> Dict[str, Any]:
    """Get store-specific extraction rules."""
    rules = {
        "spar": {
            "product": {"selector": ".product-name", "type": "text"},
            "price": {"selector": ".current-price", "type": "text"},
            "original_price": {"selector": ".original-price", "type": "text"}
        },
        "penny": {
            "product": {"selector": ".product-title", "type": "text"},
            "price": {"selector": ".price", "type": "text"},
            "discount": {"selector": ".discount-badge", "type": "text"}
        },
        "zalando": {
            "product": {"selector": "[data-testid='product-title']", "type": "text"},
            "price": {"selector": "[data-testid='price']", "type": "text"},
            "brand": {"selector": "[data-testid='brand']", "type": "text"}
        }
    }
    
    return rules.get(store_name.lower(), {})

if __name__ == "__main__":
    # Example usage
    async def main():
        api_key = "your_firecrawl_api_key"
        
        spider = FirecrawlDiscountSpider(api_key)
        await spider.setup()
        
        urls = [
            "https://example-store.com/product1",
            "https://example-store.com/product2"
        ]
        
        items = await spider.crawl_discounts(urls, "example-store")
        
        for item in items:
            print(f"Extracted: {item['name']} - {item['price']}")
    
    asyncio.run(main()) 