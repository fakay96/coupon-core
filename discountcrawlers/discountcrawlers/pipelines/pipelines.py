"""Pipelines for processing scraped discount items."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
from scrapy import Spider, Item
from scrapy.exceptions import DropItem

from .base import BasePipeline, BatchProcessingPipeline
from discountcrawlers.utils.embedding import generate_embedding
from discountcrawlers.utils.storage import upload_to_spaces
from discountcrawlers.utils.redis_utils import store_processed_url
from discountcrawlers.items import DiscountItem

LOGGER = logging.getLogger(__name__)

class DiscountPipeline:
    """Pipeline for processing discount items."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def process_item(self, item: Item, spider: Any) -> Optional[Item]:
        """Process a discount item."""
        if not isinstance(item, DiscountItem):
            return item
            
        try:
            # Validate required fields
            if not self._validate_required_fields(item):
                raise DropItem("Missing required fields")
                
            # Clean and normalize data
            item = self._clean_data(item)
            
            # Calculate discount percentage if not provided
            if not item.get('discount_percentage') and item.get('original_price') and item.get('price'):
                item['discount_percentage'] = self._calculate_discount_percentage(
                    item['original_price'],
                    item['price']
                )
                
            # Add processing metadata
            item['is_processed'] = True
            item['processing_status'] = 'success'
            
            return item
            
        except Exception as e:
            self.logger.error(f"Error processing item: {e}")
            item['processing_status'] = 'error'
            item['error_message'] = str(e)
            raise DropItem(f"Error processing item: {e}")
    
    def _validate_required_fields(self, item: DiscountItem) -> bool:
        """Validate that all required fields are present."""
        required_fields = [
            'title',
            'price',
            'product_url',
            'store_name',
            'source'
        ]
        
        missing_fields = [field for field in required_fields if not item.get(field)]
        if missing_fields:
            self.logger.warning(f"Missing required fields: {missing_fields}")
            return False
        return True
    
    def _clean_data(self, item: DiscountItem) -> DiscountItem:
        """Clean and normalize item data."""
        # Clean title
        if item.get('title'):
            item['title'] = item['title'].strip()
            
        # Clean description
        if item.get('description'):
            item['description'] = item['description'].strip()
            
        # Clean prices
        if item.get('price'):
            item['price'] = float(item['price'])
        if item.get('original_price'):
            item['original_price'] = float(item['original_price'])
            
        # Clean URLs
        if item.get('product_url'):
            item['product_url'] = item['product_url'].strip()
        if item.get('store_url'):
            item['store_url'] = item['store_url'].strip()
            
        # Clean image URLs
        if item.get('image_urls'):
            item['image_urls'] = [url.strip() for url in item['image_urls'] if url.strip()]
            
        return item
    
    def _calculate_discount_percentage(self, original_price: float, current_price: float) -> float:
        """Calculate discount percentage."""
        try:
            return ((original_price - current_price) / original_price) * 100
        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f"Error calculating discount percentage: {e}")
            return 0.0

class DealsAndEmbedPipeline(BatchProcessingPipeline):
    """Pipeline for generating embeddings and storing batched items."""
    
    def _generate_text_for_embedding(self, item: Dict[str, Any]) -> str:
        """Generate text for embedding from item fields.
        
        Args:
            item: Dictionary containing item data
            
        Returns:
            String containing concatenated text for embedding
        """
        parts = []
        
        # Add name if available (most important field)
        if item.get('name'):
            parts.append(f"Product: {item['name']}")
        
        # Add brand if available
        if item.get('brand'):
            parts.append(f"Brand: {item['brand']}")
            
        # Add category if available
        if item.get('category'):
            parts.append(f"Category: {item['category']}")
        
        # Add size if available
        if item.get('size'):
            parts.append(f"Size: {item['size']}")
        
        # Add price information
        if item.get('sale_price') is not None:
            parts.append(f"Sale Price: {item['sale_price']}")
        
        if item.get('original_price') is not None:
            parts.append(f"Original Price: {item['original_price']}")
        
        if item.get('discount_percentage') is not None:
            discount = item['discount_percentage']
            if isinstance(discount, (int, float)):
                parts.append(f"Discount: {discount}%")
            else:
                parts.append(f"Discount: {discount}")
                
        if item.get('price_per_unit') is not None:
            parts.append(f"Price Per Unit: {item['price_per_unit']}")
            
        # Add stock information if available
        if item.get('stock_info'):
            parts.append(f"Stock: {item['stock_info']}")
        
        # Add validity dates if available
        if item.get('validity_dates'):
            validity = item['validity_dates'].replace('von', 'from').replace('bis', 'to')
            parts.append(f"Valid: {validity}")
        
        # If no text fields are available, use a placeholder
        if not parts:
            LOGGER.warning(f"No text fields available for embedding generation for item: {str(item)}")
            return "Unknown product with no available description"
        
        return " | ".join(parts)
    
    def _process_batch(self, items: List[Dict[str, Any]], spider: Spider) -> None:
        """Process a batch of items by generating embeddings and storing them.
        
        Args:
            items: List of item dictionaries to process
            spider: The spider that scraped the items
        """
        try:
            # Generate text for embeddings
            texts = [self._generate_text_for_embedding(item) for item in items]
            
            # Generate embeddings and categories
            try:
                embeddings, categories = generate_embedding(texts)
            except Exception as e:
                LOGGER.error(f"Failed to generate embeddings: {e}")
                raise

            # Add embeddings and categories to items
            for i, (item, embedding, category) in enumerate(zip(items, embeddings, categories)):
                item['embedding'] = embedding.tolist()
                item['category'] = category
                
                # Store in Redis with metadata
                try:
                    store_processed_url(
                        url=item['source_url'],
                        data=json.dumps(item, ensure_ascii=False),
                        metadata={
                            'category': category,
                            'timestamp': item.get('timestamp', int(time.time())),
                            'spider': spider.name
                        }
                    )
                except Exception as e:
                    LOGGER.error(f"Failed to store item in Redis: {e}")
                    continue

            # Store batch data in JSON format
            timestamp = int(time.time())
            storage_key = f"batches/batch_{timestamp}.json"
            batch_data = {
                'timestamp': timestamp,
                'spider': spider.name,
                'items': items
            }
            
            try:
                upload_to_spaces(
                    data=json.dumps(batch_data, ensure_ascii=False),
                    key=storage_key
                )
                LOGGER.info(f"Successfully processed batch of {len(items)} items")
            except Exception as e:
                LOGGER.error(f"Failed to upload batch data: {e}")
                raise
                
        except Exception as e:
            LOGGER.error(f"Failed to process batch: {e}")
            raise