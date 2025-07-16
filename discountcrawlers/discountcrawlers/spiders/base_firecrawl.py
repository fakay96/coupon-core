"""
Base Firecrawl Spider for Discount Crawlers
==========================================

This module provides a base spider class that uses Firecrawl API for all web scraping
operations, replacing traditional Scrapy + Playwright approaches with structured
data extraction via Firecrawl.

Features:
- Automatic Firecrawl client management
- Structured data extraction with schemas
- Pagination support via Firecrawl
- Error handling and retry logic
- Integration with existing Scrapy pipeline
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Iterator, AsyncIterator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import scrapy
from scrapy import Request
from scrapy.http import Response
from scrapy.exceptions import CloseSpider

from ..firecrawl_integration import (
    FirecrawlClient, 
    FirecrawlConfig, 
    FirecrawlRequest,
    FirecrawlDiscountExtractor,
    get_store_specific_rules
)
from ..items import DiscountItem


class BaseFirecrawlSpider(scrapy.Spider):
    """Base spider class for all Firecrawl-based discount crawlers."""
    
    name: str = "base_firecrawl_spider"
    allowed_domains: list = []
    start_urls: list = []
    
    # Firecrawl configuration
    firecrawl_config: Optional[FirecrawlConfig] = None
    max_pages: int = 10
    items_per_page: int = 50
    
    # Custom settings for Firecrawl
    custom_settings: Dict[str, Any] = {
        'CONCURRENT_REQUESTS': 1,  # Firecrawl handles concurrency
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_DELAY': 1,  # Rate limiting
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'HTTPERROR_ALLOWED_CODES': [403, 429, 500, 502, 503, 504],
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Initialize Firecrawl client
        if not self.firecrawl_config:
            self.firecrawl_config = self._get_default_config()
        
        self.firecrawl_client = None
        self.extractor = None
        
    def _get_default_config(self) -> FirecrawlConfig:
        """Get default Firecrawl configuration."""
        from ..config.settings import FIRECRAWL_API_KEY
        
        return FirecrawlConfig(
            api_key=FIRECRAWL_API_KEY,
            timeout=60,
            max_retries=3,
            retry_delay=2.0,
            max_concurrent_requests=1,  # Conservative for rate limits
            enable_screenshots=False,
            enable_pdf=False,
            wait_for_timeout=10000,  # 10 seconds
        )
    
    async def start_requests(self) -> Iterator[Request]:
        """Generate initial requests using Firecrawl."""
        # Initialize Firecrawl client
        self.firecrawl_client = FirecrawlClient(self.firecrawl_config)
        self.extractor = FirecrawlDiscountExtractor(self.firecrawl_client)
        
        for url in self.start_urls:
            self.logger.info(f"Starting Firecrawl scraping for: {url}")
            yield Request(
                url=url,
                callback=self.parse,
                meta={
                    'page_num': 1,
                    'firecrawl_request': self._create_firecrawl_request(url, page_num=1)
                },
                dont_filter=True
            )
    
    def _create_firecrawl_request(self, url: str, page_num: int = 1) -> FirecrawlRequest:
        """Create a Firecrawl request configuration."""
        # Get store-specific extraction rules (for reference, not used in API call)
        store_name = self._get_store_name_from_url(url)
        extraction_rules = get_store_specific_rules(store_name)
        
        return FirecrawlRequest(
            url=url,
            formats=["markdown", "html"],
            actions=self._get_wait_actions(),
            wait_for_timeout=self.firecrawl_config.wait_for_timeout,
            screenshot=False,
            pdf=False,
            only_main_content=True,
            timeout_ms=120000
        )
    
    def _get_wait_actions(self) -> List[Dict[str, Any]]:
        """Get wait actions for dynamic content loading."""
        return [
            {
                "type": "wait",
                "timeout": self.firecrawl_config.wait_for_timeout
            }
        ]
    
    def _get_store_name_from_url(self, url: str) -> str:
        """Extract store name from URL."""
        domain = urlparse(url).netloc
        # Remove www. prefix and get first part
        store_name = domain.replace('www.', '').split('.')[0]
        return store_name
    
    async def parse(self, response: Response) -> AsyncIterator[DiscountItem]:
        """Parse response using Firecrawl."""
        current_page_num = response.meta.get('page_num', 1)
        firecrawl_request = response.meta.get('firecrawl_request')
        
        if not firecrawl_request:
            self.logger.error("No Firecrawl request found in response meta")
            return
        
        self.logger.info(f"Parsing page {current_page_num}: {response.url}")
        
        try:
            # Use Firecrawl to scrape the page
            async with self.firecrawl_client as client:
                result = await client.scrape_url(firecrawl_request)
                
                if not result or 'data' not in result:
                    self.logger.error(f"No data returned from Firecrawl for {response.url}")
                    return
                
                # Extract discount items using the extractor
                store_name = self._get_store_name_from_url(response.url)
                items = await self._extract_items_from_firecrawl_result(
                    result, response.url, store_name
                )
                
                # Yield extracted items
                items_yielded = 0
                for item in items:
                    if self._validate_item(item):
                        yield item
                        items_yielded += 1
                
                self.logger.info(f"Page {current_page_num}: Yielded {items_yielded} items")
                
                # Handle pagination
                if current_page_num < self.max_pages and items_yielded > 0:
                    next_page_url = self._get_next_page_url(response.url, current_page_num + 1)
                    if next_page_url:
                        next_request = self._create_firecrawl_request(next_page_url, current_page_num + 1)
                        yield Request(
                            url=next_page_url,
                            callback=self.parse,
                            meta={
                                'page_num': current_page_num + 1,
                                'firecrawl_request': next_request
                            },
                            dont_filter=True
                        )
        
        except Exception as e:
            self.logger.error(f"Error parsing page {current_page_num}: {e}")
            # Continue with next page if available
    
    async def _extract_items_from_firecrawl_result(
        self, 
        result: Dict[str, Any], 
        source_url: str, 
        store_name: str
    ) -> List[DiscountItem]:
        """Extract discount items from Firecrawl result."""
        items = []
        
        try:
            # Try to extract using structured data first
            if 'data' in result and isinstance(result['data'], dict):
                structured_data = result['data']
                
                # Handle different data structures
                if 'products' in structured_data:
                    # Multiple products in array
                    for product_data in structured_data['products']:
                        item = self._create_item_from_data(product_data, source_url, store_name)
                        if item:
                            items.append(item)
                
                elif 'product' in structured_data:
                    # Single product
                    item = self._create_item_from_data(structured_data['product'], source_url, store_name)
                    if item:
                        items.append(item)
                
                else:
                    # Try to extract from general data structure
                    item = self._create_item_from_data(structured_data, source_url, store_name)
                    if item:
                        items.append(item)
            
            # Fallback: extract from content if no structured data
            if not items and 'content' in result:
                content = result['content']
                if isinstance(content, str):
                    # Use the extractor to parse content
                    item = await self.extractor.extract_discount_data(source_url, store_name)
                    if item:
                        items.append(item)
        
        except Exception as e:
            self.logger.error(f"Error extracting items from Firecrawl result: {e}")
        
        return items
    
    def _create_item_from_data(
        self, 
        data: Dict[str, Any], 
        source_url: str, 
        store_name: str
    ) -> Optional[DiscountItem]:
        """Create a DiscountItem from extracted data."""
        try:
            item = DiscountItem()
            item['source_url'] = source_url
            item['store_name'] = store_name
            
            # Map common fields
            field_mapping = {
                'name': ['name', 'title', 'product_name'],
                'brand': ['brand', 'manufacturer'],
                'original_price': ['original_price', 'old_price', 'regular_price'],
                'sale_price': ['sale_price', 'current_price', 'price'],
                'discount_percentage': ['discount_percentage', 'discount', 'savings'],
                'price_per_unit': ['price_per_unit', 'unit_price'],
                'size': ['size', 'quantity', 'weight'],
                'category': ['category', 'product_category'],
                'validity_dates': ['validity_dates', 'valid_until', 'expiry'],
                'url': ['url', 'product_url', 'link'],
                'image_urls': ['image_urls', 'images', 'image'],
                'description': ['description', 'product_description']
            }
            
            for item_field, data_fields in field_mapping.items():
                for data_field in data_fields:
                    if data_field in data and data[data_field]:
                        item[item_field] = data[data_field]
                        break
            
            # Handle image URLs
            if 'image_urls' in item and isinstance(item['image_urls'], str):
                item['image_urls'] = [item['image_urls']]
            
            # Calculate discount percentage if not provided
            if not item.get('discount_percentage') and item.get('original_price') and item.get('sale_price'):
                try:
                    original = float(str(item['original_price']).replace('€', '').replace(',', '.'))
                    sale = float(str(item['sale_price']).replace('€', '').replace(',', '.'))
                    if original > 0:
                        discount = ((original - sale) / original) * 100
                        item['discount_percentage'] = f"{discount:.1f}%"
                except (ValueError, TypeError):
                    pass
            
            return item if item.get('name') or item.get('sale_price') else None
            
        except Exception as e:
            self.logger.error(f"Error creating item from data: {e}")
            return None
    
    def _validate_item(self, item: DiscountItem) -> bool:
        """Validate if an item has required fields."""
        return bool(
            item.get('name') or 
            item.get('sale_price') or 
            item.get('url')
        )
    
    def _get_next_page_url(self, current_url: str, next_page_num: int) -> Optional[str]:
        """Generate next page URL for pagination."""
        try:
            parsed_url = urlparse(current_url)
            query_params = parse_qs(parsed_url.query)
            
            # Update page parameter
            query_params['page'] = [str(next_page_num)]
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            next_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            return next_url
            
        except Exception as e:
            self.logger.error(f"Error generating next page URL: {e}")
            return None
    
    def closed(self, reason):
        """Called when the spider is closed."""
        self.logger.info(f"Firecrawl spider closed: {reason}")
        if self.firecrawl_client:
            # Clean up any remaining resources
            pass 