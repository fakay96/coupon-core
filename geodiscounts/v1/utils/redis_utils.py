"""
Utility module for Redis operations specific to geodiscounts.

Extends RedisClient functionality for discount-specific use cases.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis
from django.conf import settings

from authentication.v1.utils.redis_client import RedisClient

LOGGER = logging.getLogger(__name__)
redis_client = RedisClient()

DISCOUNT_CHANNEL = "dishpal_discount_channel"

def cache_discount_query(key: str, results: list, expiry: int = 300) -> None:
    """
    Cache discount query results in Redis.

    Args:
        key (str): The cache key.
        results (list): The query results to cache.
        expiry (int): Time-to-live (TTL) for the cache in seconds (default: 300).
    """
    redis_client.set_token(key, json.dumps(results), expiry)


def get_cached_discount_query(key: str) -> list:
    """
    Retrieve cached discount query results from Redis.

    Args:
        key (str): The cache key.

    Returns:
        list: The cached query results, or None if not found.
    """
    data = redis_client.get_token(key)
    return json.loads(data) if data else None


class RedisUtils:
    """Utility class for Redis operations."""
    
    def __init__(self) -> None:
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(settings.REDIS_URL)
        
    def store_processed_url(self, url: str, metadata: Dict[str, Any]) -> bool:
        """
        Store a processed URL and its metadata in Redis.
        
        Args:
            url: The URL to store
            metadata: Dictionary containing metadata about the URL
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Set initial status as 'pending'
            metadata['status'] = 'pending'
            
            # Store URL and metadata
            self.redis_client.hset(
                'processed_urls',
                url,
                json.dumps(metadata)
            )
            
            # Add to pending set
            self.redis_client.sadd('pending_urls', url)
            
            LOGGER.info(f"Stored URL in Redis: {url}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to store URL in Redis: {e}")
            return False
            
    def get_pending_urls(self) -> List[Dict[str, Any]]:
        """
        Get all URLs with 'pending' status from Redis.
        
        Returns:
            List of dictionaries containing URL and metadata
        """
        try:
            pending_urls = []
            urls = self.redis_client.smembers('pending_urls')
            
            for url in urls:
                url_str = url.decode('utf-8')
                metadata = self.redis_client.hget('processed_urls', url_str)
                
                if metadata:
                    metadata_dict = json.loads(metadata)
                    if metadata_dict.get('status') == 'pending':
                        pending_urls.append({
                            'url': url_str,
                            'metadata': metadata_dict
                        })
                        
            return pending_urls
            
        except Exception as e:
            LOGGER.error(f"Failed to get pending URLs from Redis: {e}")
            return []
            
    def update_url_status(self, url: str, status: str) -> bool:
        """
        Update the status of a URL in Redis.
        
        Args:
            url: The URL to update
            status: New status ('pending', 'processing', 'processed', 'failed')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current metadata
            metadata = self.redis_client.hget('processed_urls', url)
            if not metadata:
                return False
                
            # Update status
            metadata_dict = json.loads(metadata)
            metadata_dict['status'] = status
            
            # Store updated metadata
            self.redis_client.hset(
                'processed_urls',
                url,
                json.dumps(metadata_dict)
            )
            
            # Update sets based on status
            if status == 'pending':
                self.redis_client.sadd('pending_urls', url)
            else:
                self.redis_client.srem('pending_urls', url)
                
            if status == 'processing':
                self.redis_client.sadd('processing_urls', url)
            else:
                self.redis_client.srem('processing_urls', url)
                
            if status in ['processed', 'failed']:
                self.redis_client.sadd(f'{status}_urls', url)
                
            LOGGER.info(f"Updated URL status in Redis: {url} -> {status}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Failed to update URL status in Redis: {e}")
            return False
            
    def get_url_status(self, url: str) -> Optional[str]:
        """
        Get the current status of a URL from Redis.
        
        Args:
            url: The URL to check
            
        Returns:
            Optional[str]: The current status or None if not found
        """
        try:
            metadata = self.redis_client.hget('processed_urls', url)
            if metadata:
                return json.loads(metadata).get('status')
            return None
            
        except Exception as e:
            LOGGER.error(f"Failed to get URL status from Redis: {e}")
            return None



