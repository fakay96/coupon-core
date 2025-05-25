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
from discountcrawlers.items import DiscountItem
from discountcrawlers.config import settings as settings
LOGGER = logging.getLogger(__name__)
from twisted.internet import defer
from twisted.internet import threads
import requests
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
    
      
    def __init__(self, crawler=None):
        super().__init__(crawler)  # Pass crawler to parent class
        # Get settings
      
        self.api_endpoint = settings.DISCOUNT_IMPORT_API_ENDPOINT
        self.api_key = settings.DISCOUNT_IMPORT_API_KEY
        self.api_timeout = settings.DISCOUNT_IMPORT_API_TIMEOUT 
        
        if not self.api_endpoint:
            raise ValueError("DISCOUNT_IMPORT_API_ENDPOINT setting is required")
        if not self.api_key:
            raise ValueError("DISCOUNT_IMPORT_API_KEY setting is required")
            
        LOGGER.info(f"Initialized DealsAndEmbedPipeline with endpoint: {self.api_endpoint}")
    
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
    
    def _send_to_import_api(self, file_url: str, metadata: Dict[str, Any]) -> bool:
        """Send file URL to the import API endpoint.
        
        Args:
            file_url: The URL of the uploaded file
            metadata: Additional metadata about the batch
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = {
                'file_url': file_url,
                'metadata': metadata  # Optional: include metadata if your API supports it
            }
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            LOGGER.info(f"Sending import request to {self.api_endpoint} for file: {file_url}")
            
            response = requests.post(
                self.api_endpoint,
                json=payload,
                headers=headers,
                timeout=self.api_timeout
            )
            
            if response.status_code == 202:  # HTTP_202_ACCEPTED
                response_data = response.json()
                task_id = response_data.get('task_id', 'unknown')
                LOGGER.info(f"Import task scheduled successfully. Task ID: {task_id}, File: {file_url}")
                return True
            else:
                LOGGER.error(f"API request failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            LOGGER.error(f"Timeout when calling import API for file: {file_url}")
            return False
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Request exception when calling import API: {e}")
            return False
        except Exception as e:
            LOGGER.error(f"Unexpected error when calling import API: {e}")
            return False
    
    def _send_to_import_api_async(self, file_url: str, metadata: Dict[str, Any]):
        """Async wrapper for sending to import API."""
        return threads.deferToThread(self._send_to_import_api, file_url, metadata)
    
    @defer.inlineCallbacks
    def _process_batch(self, items: List[Dict[str, Any]], spider: Spider):
        """Process a batch of items and return a Deferred firing with items."""
        try:
            # Embedding generation
            texts = [self._generate_text_for_embedding(item) for item in items]
            embeddings, categories = generate_embeddings_batch(texts)
            for item, emb, cat in zip(items, embeddings, categories):
                item['embedding'] = emb.tolist()
                item['category'] = cat

            # Prepare batch upload
            timestamp = int(time.time())
            storage_key = f"batches/batch_{timestamp}.json"
            batch_data = {
                'timestamp': timestamp,
                'spider': spider.name,
                'items': items,
                'item_count': len(items),
                'batch_id': f"batch_{timestamp}"
            }
            json_data = json.dumps(batch_data, ensure_ascii=False)

            # Upload to spaces and await URL
            url = yield defer.maybeDeferred(upload_to_spaces, json_data, storage_key)
            LOGGER.info(f"Successfully uploaded batch of {len(items)} items to {url}")

            # Send to import API
            metadata = {
                'storage_key': storage_key,
                'timestamp': timestamp,
                'spider': spider.name,
                'item_count': len(items),
                'batch_id': f"batch_{timestamp}",
                'type': 'json'
            }
            success = yield self._send_to_import_api_async(url, metadata)
            if success:
                LOGGER.info(f"Successfully sent import request for batch: {url}")
            else:
                LOGGER.error(f"Failed to send import request for batch: {url}")

        except Exception as e:
            LOGGER.error(f"Failed to process batch: {e}")
        # Always return items, even on error
        defer.returnValue(items)
