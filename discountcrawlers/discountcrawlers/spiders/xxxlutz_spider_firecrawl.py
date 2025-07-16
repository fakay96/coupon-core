"""
XXXLUTZ Spider using Firecrawl
================================

This spider scrapes discount products from XXXLUTZ using Firecrawl API
for enhanced data extraction and JavaScript rendering.

Features:
- Structured data extraction via Firecrawl
- Automatic pagination handling
- Product information extraction
- Price and discount calculation
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .base_firecrawl import BaseFirecrawlSpider
from ..items import DiscountItem
from ..config.settings import get_store_config


class XxxlutzFirecrawlSpider(BaseFirecrawlSpider):
    """XXXLUTZ spider using Firecrawl for enhanced scraping."""
    
    name = "xxxlutz_spider_firecrawl"
    allowed_domains = []
    start_urls = []
    
    # Store-specific configuration
    store_config = get_store_config('xxxlutz')
    max_pages = store_config.get('max_pages', 10)
    items_per_page = store_config.get('items_per_page', 50)
    
    # Custom settings for XXXLUTZ
    custom_settings = {
        **BaseFirecrawlSpider.custom_settings,
        'DOWNLOAD_DELAY': 1.5,  # XXXLUTZ rate limiting
        'AUTOTHROTTLE_START_DELAY': 1.5,
        'AUTOTHROTTLE_MAX_DELAY': 10,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def _get_wait_actions(self) -> list:
        """Get wait actions specific to XXXLUTZ."""
        return [
            {
                "type": "wait",
                "timeout": 3000  # Wait for dynamic content
            },
            {
                "type": "wait_for_selector",
                "selector": ".product-card, .product-item, li[data-test*='product']",
                "timeout": 8000
            }
        ]
    
    def _get_store_name_from_url(self, url: str) -> str:
        """Extract store name from URL."""
        return "xxxlutz"
    
    async def _extract_items_from_firecrawl_result(
        self, 
        result: Dict[str, Any], 
        source_url: str, 
        store_name: str
    ) -> list[DiscountItem]:
        """Extract discount items from Firecrawl result with XXXLUTZ-specific logic."""
        items = []
        
        try:
            # Try to extract using structured data first
            if 'data' in result and isinstance(result['data'], dict):
                structured_data = result['data']
                
                # Handle XXXLUTZ's product structure
                if 'products' in structured_data:
                    # Multiple products in array
                    for product_data in structured_data['products']:
                        item = self._create_xxxlutz_item_from_data(product_data, source_url, store_name)
                        if item:
                            items.append(item)
                
                elif 'product' in structured_data:
                    # Single product
                    item = self._create_xxxlutz_item_from_data(structured_data['product'], source_url, store_name)
                    if item:
                        items.append(item)
                
                else:
                    # Try to extract from general data structure
                    item = self._create_xxxlutz_item_from_data(structured_data, source_url, store_name)
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
    
    def _create_xxxlutz_item_from_data(
        self, 
        data: Dict[str, Any], 
        source_url: str, 
        store_name: str
    ) -> Optional[DiscountItem]:
        """Create a DiscountItem from XXXLUTZ data with specific field mapping."""
        try:
            item = DiscountItem()
            item['source_url'] = source_url
            item['store_name'] = store_name
            item['source'] = 'xxxlutz'
            
            # XXXLUTZ-specific field mapping
            field_mapping = {
                'name': ['name', 'title', 'product_name', 'product-title'],
                'brand': ['brand', 'manufacturer'],
                'sale_price': ['sale_price', 'current_price', 'price', 'price-current'],
                'original_price': ['original_price', 'old_price', 'regular_price', 'price-old'],
                'discount_percentage': ['discount_percentage', 'discount', 'savings'],
                'size': ['size', 'quantity', 'weight'],
                'validity_dates': ['validity_dates', 'valid_until', 'expiry'],
                'url': ['url', 'product_url', 'link'],
                'image_urls': ['image_urls', 'images', 'image'],
                'category': ['category', 'product_category']
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
                    original = self._parse_xxxlutz_price(item['original_price'])
                    sale = self._parse_xxxlutz_price(item['sale_price'])
                    if original and sale and original > 0:
                        discount = ((original - sale) / original) * 100
                        item['discount_percentage'] = f"{discount:.1f}%"
                except (ValueError, TypeError):
                    pass
            
            # Clean and validate the item
            item = self._clean_xxxlutz_item(item)
            
            return item if self._validate_xxxlutz_item(item) else None
            
        except Exception as e:
            self.logger.error(f"Error creating XXXLUTZ item from data: {e}")
            return None
    
    def _parse_xxxlutz_price(self, price_str: str) -> Optional[float]:
        """Parse XXXLUTZ price format."""
        if not price_str:
            return None
        
        try:
            # Remove currency symbols and clean
            import re
            cleaned = re.sub(r'[^\d,.]', '', str(price_str))
            
            # Handle European decimal format
            if ',' in cleaned and '.' in cleaned:
                # Format: 1.234,56 -> 1234.56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Check if comma is decimal separator
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _clean_xxxlutz_item(self, item: DiscountItem) -> DiscountItem:
        """Clean and normalize XXXLUTZ item data."""
        # Clean price fields
        for price_field in ['sale_price', 'original_price']:
            if item.get(price_field):
                item[price_field] = str(item[price_field]).strip()
        
        # Clean text fields
        for text_field in ['name', 'brand', 'size', 'category', 'validity_dates']:
            if item.get(text_field):
                item[text_field] = str(item[text_field]).strip()
        
        # Ensure URL is absolute
        if item.get('url') and not item['url'].startswith('http'):
            if item['url'].startswith('/'):
                item['url'] = f"https://www.xxxlutz.at{item['url']}"
            else:
                item['url'] = f"https://www.xxxlutz.at/{item['url']}"
        
        return item
    
    def _validate_xxxlutz_item(self, item: DiscountItem) -> bool:
        """Validate if a XXXLUTZ item has required fields."""
        # XXXLUTZ items should have at least a name or sale price
        return bool(
            item.get('name') or 
            item.get('sale_price') or 
            item.get('url')
        )
    
    def _get_next_page_url(self, current_url: str, next_page_num: int) -> Optional[str]:
        """Generate next page URL for XXXLUTZ pagination."""
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
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
