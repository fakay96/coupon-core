"""
Enhanced Spider with Firecrawl Integration
=========================================

This spider demonstrates how to integrate Firecrawl API with existing Scrapy
infrastructure for enhanced structured data extraction from discount sites.
"""

import asyncio
import logging
from typing import Iterator, Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy import Request
from scrapy.http import Response
from scrapy.exceptions import CloseSpider

from .base import BaseDiscountSpider
from discountcrawlers.items import DiscountItem
from discountcrawlers.firecrawl_integration import (
    FirecrawlClient, 
    FirecrawlConfig, 
    FirecrawlDiscountExtractor,
    FirecrawlRequest,
    get_store_specific_rules
)

LOGGER = logging.getLogger(__name__)

class FirecrawlEnhancedSpider(BaseDiscountSpider):
    """
    Enhanced spider that uses Firecrawl for structured data extraction.
    
    This spider combines traditional Scrapy crawling with Firecrawl's
    advanced extraction capabilities for better data quality.
    """
    
    name = "firecrawl_enhanced"
    allowed_domains = ["interspar.at", "penny.at", "zalando.at", "mueller.at"]
    
    # Store-specific configurations
    store_configs = {
        "spar": {
            "start_urls": [
                "https://www.interspar.at/shop/lebensmittel/search/?filter=is-on-promotion:true&hitsPerPage=80&page=1"
            ],
            "product_selector": "div.productBox[data-url]",
            "extraction_rules": {
                "product": {"selector": ".product-name", "type": "text"},
                "price": {"selector": ".current-price", "type": "text"},
                "original_price": {"selector": ".original-price", "type": "text"},
                "brand": {"selector": ".brand-name", "type": "text"},
                "images": {"selector": ".product-image img", "type": "attribute", "attribute": "src"}
            }
        },
        "penny": {
            "start_urls": [
                "https://www.penny.at/angebote"
            ],
            "product_selector": ".product-card",
            "extraction_rules": {
                "product": {"selector": ".product-title", "type": "text"},
                "price": {"selector": ".price", "type": "text"},
                "discount": {"selector": ".discount-badge", "type": "text"},
                "brand": {"selector": ".brand", "type": "text"}
            }
        },
        "zalando": {
            "start_urls": [
                "https://www.zalando.at/sale/"
            ],
            "product_selector": "[data-testid='product-card']",
            "extraction_rules": {
                "product": {"selector": "[data-testid='product-title']", "type": "text"},
                "price": {"selector": "[data-testid='price']", "type": "text"},
                "brand": {"selector": "[data-testid='brand']", "type": "text"},
                "images": {"selector": "[data-testid='product-image']", "type": "attribute", "attribute": "src"}
            }
        }
    }
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 4,  # Reduced for API rate limits
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'HTTPERROR_ALLOWED_CODES': [403, 429, 500, 502, 503, 504],
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
    }
    
    def __init__(self, store_name: str = "spar", firecrawl_api_key: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store_name = store_name.lower()
        self.firecrawl_api_key = firecrawl_api_key
        self.firecrawl_client = None
        self.firecrawl_extractor = None
        
        # Set store-specific configuration
        if self.store_name in self.store_configs:
            config = self.store_configs[self.store_name]
            self.start_urls = config["start_urls"]
            self.product_selector = config["product_selector"]
            self.extraction_rules = config["extraction_rules"]
        else:
            raise ValueError(f"Unsupported store: {store_name}")
        
        # Initialize Firecrawl if API key is provided
        if self.firecrawl_api_key:
            self._setup_firecrawl()
    
    def _setup_firecrawl(self):
        """Setup Firecrawl client and extractor."""
        try:
            config = FirecrawlConfig(
                api_key=self.firecrawl_api_key,
                wait_for_selectors=[".product-title", ".price", ".product-price"],
                enable_screenshots=False,
                enable_pdf=False,
                max_concurrent_requests=5,
                timeout=30
            )
            
            self.firecrawl_client = FirecrawlClient(config)
            self.firecrawl_extractor = FirecrawlDiscountExtractor(self.firecrawl_client)
            
            LOGGER.info(f"Firecrawl initialized for {self.store_name}")
            
        except Exception as e:
            LOGGER.error(f"Failed to initialize Firecrawl: {e}")
            self.firecrawl_client = None
            self.firecrawl_extractor = None
    
    def start_requests(self) -> Iterator[Request]:
        """Generate initial requests."""
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={'store_name': self.store_name},
                errback=self.handle_error
            )
    
    def parse(self, response: Response) -> Iterator[Dict[str, Any]]:
        """Parse the main page and extract product URLs."""
        store_name = response.meta.get('store_name', self.store_name)
        
        # Extract product URLs
        product_links = response.css(f"{self.product_selector} a::attr(href)").getall()
        
        for link in product_links:
            product_url = urljoin(response.url, link)
            
            if self.firecrawl_extractor:
                # Use Firecrawl for enhanced extraction
                yield Request(
                    url=product_url,
                    callback=self.parse_with_firecrawl,
                    meta={'store_name': store_name},
                    errback=self.handle_error
                )
            else:
                # Fallback to traditional Scrapy parsing
                yield Request(
                    url=product_url,
                    callback=self.parse_traditional,
                    meta={'store_name': store_name},
                    errback=self.handle_error
                )
        
        # Handle pagination if needed
        next_page = self._get_next_page(response)
        if next_page:
            yield Request(
                url=next_page,
                callback=self.parse,
                meta={'store_name': store_name},
                errback=self.handle_error
            )
    
    def parse_with_firecrawl(self, response: Response) -> Iterator[DiscountItem]:
        """Parse product page using Firecrawl for enhanced extraction."""
        store_name = response.meta.get('store_name', self.store_name)
        
        try:
            # Create async task for Firecrawl extraction
            loop = asyncio.get_event_loop()
            item = loop.run_until_complete(
                self._extract_with_firecrawl(response.url, store_name)
            )
            
            if item:
                yield item
            else:
                # Fallback to traditional parsing if Firecrawl fails
                LOGGER.warning(f"Firecrawl extraction failed for {response.url}, falling back to traditional parsing")
                yield from self.parse_traditional(response)
                
        except Exception as e:
            LOGGER.error(f"Error in Firecrawl parsing for {response.url}: {e}")
            # Fallback to traditional parsing
            yield from self.parse_traditional(response)
    
    async def _extract_with_firecrawl(self, url: str, store_name: str) -> Optional[DiscountItem]:
        """Extract data using Firecrawl API."""
        if not self.firecrawl_extractor:
            return None
        
        try:
            # Use store-specific extraction rules
            store_rules = get_store_specific_rules(store_name)
            if store_rules:
                # Override default rules with store-specific ones
                self.firecrawl_extractor.discount_extraction_rules.update(store_rules)
            
            return await self.firecrawl_extractor.extract_discount_data(url, store_name)
            
        except Exception as e:
            LOGGER.error(f"Firecrawl extraction error for {url}: {e}")
            return None
    
    def parse_traditional(self, response: Response) -> Iterator[DiscountItem]:
        """Traditional Scrapy parsing as fallback."""
        store_name = response.meta.get('store_name', self.store_name)
        
        try:
            item = DiscountItem()
            item['url'] = response.url
            item['source'] = store_name
            item['source_url'] = response.url
            
            # Extract basic information using CSS selectors
            item['name'] = response.css('h1::text, .product-title::text, .product-name::text').get('')
            item['title'] = item['name']
            item['brand'] = response.css('.brand::text, .brand-name::text').get('')
            item['description'] = response.css('.description::text, .product-description::text').get('')
            
            # Extract prices
            price_text = response.css('.price::text, .current-price::text, [data-testid="price"]::text').get('')
            original_price_text = response.css('.original-price::text, .old-price::text, .was-price::text').get('')
            
            item['price'] = self._clean_price(price_text)
            item['original_price'] = self._clean_price(original_price_text)
            
            # Calculate discount percentage
            if item['price'] and item['original_price']:
                try:
                    original = float(item['original_price'])
                    current = float(item['price'])
                    if original > current:
                        item['discount_percentage'] = round(((original - current) / original) * 100, 2)
                except (ValueError, ZeroDivisionError):
                    pass
            
            # Extract images
            image_urls = response.css('img[src*="product"]::attr(src), .product-image img::attr(src)').getall()
            item['image_urls'] = [urljoin(response.url, img) for img in image_urls]
            
            # Extract stock information
            item['stock_info'] = response.css('.stock::text, .availability::text').get('')
            
            # Set metadata
            item['crawled_at'] = datetime.utcnow().isoformat()
            item['currency'] = 'EUR'
            item['country'] = 'Austria'
            
            # Finalize the item
            item.finalize()
            
            yield item
            
        except Exception as e:
            LOGGER.error(f"Error in traditional parsing for {response.url}: {e}")
    
    def _get_next_page(self, response: Response) -> Optional[str]:
        """Get next page URL for pagination."""
        # Store-specific pagination logic
        if self.store_name == "spar":
            # Check if there's a next page button
            next_page = response.css('.pagination .next a::attr(href)').get()
            if next_page:
                return urljoin(response.url, next_page)
        
        elif self.store_name == "penny":
            # Penny might use different pagination
            next_page = response.css('.pagination-next::attr(href)').get()
            if next_page:
                return urljoin(response.url, next_page)
        
        return None
    
    def _clean_price(self, price_str: str) -> Optional[float]:
        """Clean and convert price string to float."""
        if not price_str:
            return None
        
        import re
        # Remove currency symbols and non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.,]', '', price_str.strip())
        
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
    
    def handle_error(self, failure):
        """Handle request failures."""
        LOGGER.error(f"Request failed: {failure.value}")
        return None
    
    def closed(self, reason):
        """Called when the spider is closed."""
        LOGGER.info(f"FirecrawlEnhancedSpider closed: {reason}")
        
        # Cleanup Firecrawl resources
        if self.firecrawl_client:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup
                    loop.create_task(self._cleanup_firecrawl())
                else:
                    loop.run_until_complete(self._cleanup_firecrawl())
            except Exception as e:
                LOGGER.error(f"Error during Firecrawl cleanup: {e}")
    
    async def _cleanup_firecrawl(self):
        """Cleanup Firecrawl resources."""
        if self.firecrawl_client:
            await self.firecrawl_client.__aexit__(None, None, None)

# Example usage and configuration
class SparFirecrawlSpider(FirecrawlEnhancedSpider):
    """Spar-specific spider with Firecrawl integration."""
    name = "spar_firecrawl"
    
    def __init__(self, firecrawl_api_key: str = None, *args, **kwargs):
        super().__init__(
            store_name="spar",
            firecrawl_api_key=firecrawl_api_key,
            *args, **kwargs
        )

class PennyFirecrawlSpider(FirecrawlEnhancedSpider):
    """Penny-specific spider with Firecrawl integration."""
    name = "penny_firecrawl"
    
    def __init__(self, firecrawl_api_key: str = None, *args, **kwargs):
        super().__init__(
            store_name="penny",
            firecrawl_api_key=firecrawl_api_key,
            *args, **kwargs
        )

class ZalandoFirecrawlSpider(FirecrawlEnhancedSpider):
    """Zalando-specific spider with Firecrawl integration."""
    name = "zalando_firecrawl"
    
    def __init__(self, firecrawl_api_key: str = None, *args, **kwargs):
        super().__init__(
            store_name="zalando",
            firecrawl_api_key=firecrawl_api_key,
            *args, **kwargs
        ) 