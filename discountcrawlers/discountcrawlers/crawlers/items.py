# filename: discountcrawlers/items.py
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import scrapy
from typing import Optional, Dict, Any
from django.contrib.gis.geos import Point

class DiscountItem(scrapy.Item):
    """Item representing a discount.
    
    Attributes:
        retailer: Name of the retailer offering the discount
        category: Category of the discount
        description: Description of the discount
        discount_code: Unique code for the discount
        discount_value: Value of the discount (amount or percentage)
        is_active: Whether the discount is currently active
        expiration_date: Expiration date of the discount
        location: Geographic location where the discount is valid
        image_url: URL of the discount image
        metadata_url: URL of the discount metadata
        metadata: Additional metadata about the discount
    """
    
    retailer = scrapy.Field()
    category = scrapy.Field()
    description = scrapy.Field()
    discount_code = scrapy.Field()
    discount_value = scrapy.Field()
    is_active = scrapy.Field()
    expiration_date = scrapy.Field()
    location = scrapy.Field()
    image_url = scrapy.Field()
    metadata_url = scrapy.Field()
    metadata = scrapy.Field()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the item to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the item
        """
        data = dict(self)
        
        # Convert Point to dict if present
        if 'location' in data and isinstance(data['location'], Point):
            data['location'] = {
                'lat': data['location'].y,
                'lng': data['location'].x
            }
            
        return data

@dataclass
class DiscountData:
    """Typed representation of a discounted product.
    All fields are optional to match DiscountItem flexibility.
    """
    url: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    sale_price: Optional[str] = None
    original_price: Optional[str] = None
    discount_percentage: Optional[str] = None
    price_per_unit: Optional[str] = None
    size: Optional[str] = None
    validity_dates: Optional[str] = None
    source_url: Optional[str] = None
    stock_info: Optional[str] = None
    category: Optional[str] = None
    timestamp: Optional[str] = None
    embedding: Optional[list[float]] = None

    def to_item(self) -> DiscountItem:
        """Convert to a DiscountItem, excluding None values."""
        item = DiscountItem()
        for k, v in asdict(self).items():
            if v is not None:
                item[k] = v
        return item

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self, *, ensure_ascii: bool = False, **kwargs) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, **kwargs)