"""Items for the discount crawlers project."""

import scrapy
from typing import Optional, List, Dict, Any
from datetime import datetime


class DiscountItem(scrapy.Item):
    """Item representing a discount from a retailer."""
    
    # Basic information
    title = scrapy.Field()
    description = scrapy.Field()
    price = scrapy.Field()
    original_price = scrapy.Field()
    discount_percentage = scrapy.Field()
    currency = scrapy.Field()
    
    # Product details
    product_id = scrapy.Field()
    product_url = scrapy.Field()
    image_urls = scrapy.Field()
    category = scrapy.Field()
    brand = scrapy.Field()
    
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
    metadata = scrapy.Field()  # Dict for any additional data
    source = scrapy.Field()  # Source website/API
    source_id = scrapy.Field()  # Unique identifier from source
    
    # Processing flags
    is_processed = scrapy.Field()
    processing_status = scrapy.Field()
    error_message = scrapy.Field()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default values
        self.setdefault('crawled_at', datetime.utcnow().isoformat())
        self.setdefault('image_urls', [])
        self.setdefault('metadata', {})
        self.setdefault('is_processed', False)
        self.setdefault('processing_status', 'pending')
    
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
        return item 