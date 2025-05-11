"""Pipelines for processing scraped discount items."""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
from scrapy import Spider, Item
from scrapy.exceptions import DropItem

from .base import BasePipeline, BatchProcessingPipeline
from discountcrawlers.utils.embedding import generate_embedding,generate_embeddings_batch
from discountcrawlers.utils.storage import upload_to_spaces
from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.items import DiscountItem

LOGGER = logging.getLogger(__name__)
redis_utils = RedisUtils()
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
        """Generate text for embedding from item data"""
        # Extract relevant fields
        title = item.get('title', '')
        name = item.get('name', '')
        brand = item.get('brand', '')
        category = item.get('category', '')
        store_name = item.get('store_name', '')
        size = item.get('size', '')
        description = item.get('description', '')
        
        # Combine fields into a single string
        text_parts = []
        if title:
            text_parts.append(f"Title: {title}")
        if name and name != title:
            text_parts.append(f"Name: {name}")
        if brand:
            text_parts.append(f"Brand: {brand}")
        if category:
            text_parts.append(f"Category: {category}")
        if store_name:
            text_parts.append(f"Store: {store_name}")
        if size:
            text_parts.append(f"Size: {size}")
        if description:
            text_parts.append(f"Description: {description}")
        
        text = " | ".join(text_parts)
        
        # Log the generated text for debugging
        LOGGER.debug(f"Generated text for embedding: {text[:200]}...")
        
        return text
    
    def _process_batch(self, items: List[Dict[str, Any]], spider: Spider) -> List[Dict[str, Any]]:
        """Process a batch of items"""
        # Generate texts for embedding
        texts = [self._generate_text_for_embedding(item) for item in items]
        
        # Log sample of texts for debugging
        LOGGER.debug(f"Processing batch of {len(texts)} items")
        if texts:
            LOGGER.debug(f"Sample text: {texts[0][:200]}...")
        
        # Get embeddings and categories
        embeddings, categories = generate_embeddings_batch(texts)
        
        # Log results for debugging
        LOGGER.debug(f"Generated {len(embeddings)} embeddings and {len(categories)} categories")
        if embeddings:
            LOGGER.debug(f"First embedding shape: {embeddings[0].shape}")
            LOGGER.debug(f"First category: {categories[0]}")
        
        # Update items with embeddings and categories
        for item, embedding, category in zip(items, embeddings, categories):
            item['embedding'] = embedding.tolist()
            item['category'] = category
            
        # Store batch data in S3
        timestamp = int(time.time())
        storage_key = f"batches/batch_{timestamp}.json"
        batch_data = {
            'timestamp': timestamp,
            'spider': spider.name,
            'items': items
        }
        
        try:
            # Convert batch_data to JSON string before uploading
            json_data = json.dumps(batch_data, ensure_ascii=False)
            # Use defer.maybeDeferred to handle the upload properly
            from twisted.internet import defer
            d = defer.maybeDeferred(upload_to_spaces, json_data, storage_key)
            
            def on_upload_success(url):
                """Handle successful upload by publishing to Redis"""
                LOGGER.info(f"Successfully uploaded batch of {len(items)} items to {url}")
                
                # Store batch in Redis with 24-hour expiration
                batch_id = f"batch_{timestamp}"
                if redis_utils.store_batch(batch_id, items):
                    LOGGER.info(f"Stored batch {batch_id} in Redis")
                    
                    # Store URL metadata
                    metadata = {
                        'url': url,
                        'key': storage_key,
                        'timestamp': timestamp,
                        'spider': spider.name,
                        'type': 'json',
                        'item_count': len(items),
                        'batch_id': batch_id
                    }
                    
                    if redis_utils.store_processed_url(url, metadata):
                        LOGGER.info(f"Stored URL metadata in Redis: {url}")
                    else:
                        LOGGER.error(f"Failed to store URL metadata in Redis: {url}")
                else:
                    LOGGER.error(f"Failed to store batch {batch_id} in Redis")
                
                return url
            
            d.addCallback(on_upload_success)
            d.addErrback(lambda failure: LOGGER.error(f"Failed to upload batch data: {failure.value}"))
            
        except Exception as e:
            LOGGER.error(f"Failed to process batch: {e}")
            raise
        
        return items