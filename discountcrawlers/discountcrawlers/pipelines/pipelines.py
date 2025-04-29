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

class DiscountPipeline(BasePipeline):
    """Pipeline for processing discount items."""
    
    def _process_item(self, item: Dict[str, Any], spider: Spider) -> Optional[Dict[str, Any]]:
        """Process a discount item.
        
        Args:
            item: The item to process
            spider: The spider that yielded the item
            
        Returns:
            Optional[Dict[str, Any]]: The processed item or None if processing failed
        """
        try:
            # First clean and normalize data
            item = self._clean_data(item)
            
            # Then validate required fields
            if not self._validate_required_fields(item):
                raise DropItem("Missing required fields")
                
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
            LOGGER.error(f"Error processing item: {e}")
            item['processing_status'] = 'error'
            item['error_message'] = str(e)
            raise DropItem(f"Error processing item: {e}")
    
    def _validate_required_fields(self, item: Dict[str, Any]) -> bool:
        """Validate that all required fields are present."""
        required_fields = [
            'title',
            'product_url',
            'store_name',
            'source'
        ]
        
        missing_fields = [field for field in required_fields if not item.get(field)]
        if missing_fields:
            LOGGER.warning(f"Missing required fields: {missing_fields}")
            return False
        return True
    
    def _clean_data(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize item data."""
        # Clean title
        if item.get('title'):
            item['title'] = item['title'].strip()
            
        # Clean description
        if item.get('description'):
            item['description'] = item['description'].strip()
            
        # Clean prices
        def clean_price(price):
            if not price:
                return None
            try:
                # Handle string prices
                if isinstance(price, str):
                    # Remove currency symbols and whitespace
                    price = price.replace('€', '').replace('*', '').strip()
                    # Remove all non-numeric characters except decimal point
                    price = ''.join(c for c in price if c.isdigit() or c == '.')
                    # Handle empty string after cleaning
                    if not price:
                        return None
                return float(price)
            except (ValueError, TypeError):
                LOGGER.warning(f"Could not convert price to float: {price}")
                return None
            
        # Clean price fields
        if 'price' in item:
            item['price'] = clean_price(item['price'])
        if 'original_price' in item:
            item['original_price'] = clean_price(item['original_price'])
        if 'sale_price' in item:
            item['sale_price'] = clean_price(item['sale_price'])
            
        # If price is None but sale_price exists, use sale_price
        if item.get('price') is None and item.get('sale_price') is not None:
            item['price'] = item['sale_price']
            
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
            LOGGER.error(f"Error calculating discount percentage: {e}")
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
        print(item)
        
        # Add title if available (most important field)
        if item.get('title'):
            parts.append(f"Product: {item['title']}")
        
        # Add brand if available
        if item.get('brand'):
            parts.append(f"Brand: {item['brand']}")
            
        # Add category if available
        if item.get('category'):
            parts.append(f"Category: {item['category']}")
        
        # Add price information
        if item.get('price') is not None:
            parts.append(f"Price: {item['price']}")
        
        if item.get('original_price') is not None:
            parts.append(f"Original Price: {item['original_price']}")
        
        if item.get('discount_percentage') is not None:
            discount = item['discount_percentage']
            if isinstance(discount, (int, float)):
                parts.append(f"Discount: {discount}%")
            else:
                parts.append(f"Discount: {discount}")
        
        # Add description if available
        if item.get('description'):
            parts.append(f"Description: {item['description']}")
        
        # Add validity dates if available
        if item.get('valid_from') and item.get('valid_until'):
            parts.append(f"Valid: {item['valid_from']} to {item['valid_until']}")
        
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
                        url=item['product_url'],  # Use product_url instead of source_url
                        data=json.dumps(item, ensure_ascii=False),
                        metadata={
                            'category': category,
                            'timestamp': item.get('crawled_at', int(time.time())),
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