"""Scrapy items for discount crawlers.

This module defines the item classes used by the discount crawlers to store
scraped data in a structured format.
"""

import scrapy
from typing import Optional, List, Dict, Any
from datetime import datetime


class DiscountItem(scrapy.Item):
    """Item for storing discount product information.
    
    This item class defines the structure for storing discount information
    scraped from various retailers. All fields are optional to accommodate
    different data availability across sources.
    
    Attributes:
        url: URL of the product page
        source_url: URL where the product was found
        brand: Brand name of the product
        name: Product name
        original_price: Original price before discount
        sale_price: Current sale price
        discount_percentage: Percentage discount (e.g., "20%")
        price_per_unit: Price per unit (e.g., "€2.99/100g")
        size: Product size/quantity
        stock_info: Stock availability information
        category: Product category
        validity_dates: Date range for the discount
        timestamp: When the item was scraped
        embedding: Optional vector embedding for the product
    """
    
    # Product identification
    url = scrapy.Field()
    source_url = scrapy.Field()
    brand = scrapy.Field()
    name = scrapy.Field()
    
    # Pricing information
    original_price = scrapy.Field()
    sale_price = scrapy.Field()
    discount_percentage = scrapy.Field()
    price_per_unit = scrapy.Field()
    
    # Product details
    size = scrapy.Field()
    stock_info = scrapy.Field()
    category = scrapy.Field()
    validity_dates = scrapy.Field()
    
    # Metadata
    timestamp = scrapy.Field()
    embedding = scrapy.Field()
    
    # Basic information
    title = scrapy.Field()
    description = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    source = scrapy.Field()
    source_id = scrapy.Field()
    
    # Product details
    product_id = scrapy.Field()
    product_url = scrapy.Field()
    image_urls = scrapy.Field()
    
    # Store information
    store_name = scrapy.Field()
    store_id = scrapy.Field()
    store_url = scrapy.Field()
    
    # Location information
    location = scrapy.Field()  # GeoJSON Point
    address = scrapy.Field()
    city = scrapy.Field()
    state = scrapy.Field()
    country = scrapy.Field()
    postal_code = scrapy.Field()
    
    # Timing information
    valid_from = scrapy.Field()
    valid_until = scrapy.Field()
    crawled_at = scrapy.Field()
    
    # Additional metadata
    metadata = scrapy.Field()
    
    # Processing flags
    is_processed = scrapy.Field()
    processing_status = scrapy.Field()
    error_message = scrapy.Field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set standard defaults immediately
        self.setdefault('crawled_at', datetime.utcnow().isoformat())
        self.setdefault('image_urls', [])
        self.setdefault('metadata', {})
        self.setdefault('is_processed', False)
        self.setdefault('processing_status', 'pending')
        self.setdefault('currency', 'EUR')  # Default currency for Austrian stores
        self.setdefault('country', 'Austria')  # Default country
        self.setdefault('discount_percentage', None)
        self.setdefault('brand', None)
        self.setdefault('category', None)
        self.setdefault('valid_from', None)
        self.setdefault('valid_until', None)
        self.setdefault('address', None)
        self.setdefault('city', None)
        self.setdefault('state', None)
        self.setdefault('postal_code', None)
        self.setdefault('location', None)
        self.setdefault('description', None)
        self.setdefault('source', None)
        self.setdefault('source_id', None)
        self.setdefault('product_id', None)
        self.setdefault('product_url', None)
        self.setdefault('store_name', None)
        self.setdefault('store_id', None)
        self.setdefault('store_url', None)
        self.setdefault('price_per_unit', None)
        self.setdefault('stock_info', None)
        self.setdefault('embedding', None)
        self.setdefault('error_message', None)

    def finalize(self):
        """Finalize the item: calculate discount, fill missing values."""
        if self.get('price') is not None and self.get('original_price') is not None:
            try:
                self['discount_percentage'] = round(
                    (1 - (float(self['price']) / float(self['original_price']))) * 100, 2
                )
            except (ValueError, ZeroDivisionError):
                self['discount_percentage'] = None
        
        if not self.get('store_name') and self.get('source'):
            # Try fallback: use domain as store_name if missing
            self['store_name'] = self['source'].split('.')[0].capitalize()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the item to a dictionary."""
        return dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscountItem':
        """Create a DiscountItem from a dictionary."""
        item = cls()
        for key, value in data.items():
            if key in item.fields:
                item[key] = value
        item.finalize()
        return item
