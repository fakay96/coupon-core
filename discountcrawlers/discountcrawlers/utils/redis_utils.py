"""Redis utilities for asynchronous message processing.

This module provides functions for interacting with Redis as a message broker
for asynchronous processing of discount data.
"""

from __future__ import annotations
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import redis
from dotenv import load_dotenv
import os
import time

load_dotenv()

LOGGER: logging.Logger = logging.getLogger(__name__)

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# Queue names
SEARCH_QUEUE = "discount_search_queue"
RESULTS_QUEUE = "discount_results_queue"
# Add missing set name for processed URLs
PROCESSED_URLS = "processed_urls_set"

def get_redis_client() -> Optional[redis.Redis]:
    """Initialize and return a Redis client.
    
    Returns:
        Redis client instance or None if initialization fails
    """
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        # Test connection
        client.ping()
        return client
    except Exception as e:
        LOGGER.error(f"Failed to initialize Redis client: {str(e)}")
        return None

def queue_search_request(
    search_terms: List[str],
    categories: List[str],
    price_range: Dict[str, Optional[float]],
    filters: List[str],
    request_id: str
) -> bool:
    """Queue a search request for asynchronous processing.
    
    Args:
        search_terms: List of search terms
        categories: List of categories to search in
        price_range: Dictionary with min and max price
        filters: List of additional filters
        request_id: Unique identifier for the request
        
    Returns:
        True if queuing was successful, False otherwise
    """
    try:
        client = get_redis_client()
        if not client:
            return False
            
        # Prepare search request
        request = {
            'request_id': request_id,
            'search_terms': search_terms,
            'categories': categories,
            'price_range': price_range,
            'filters': filters,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to search queue
        client.lpush(SEARCH_QUEUE, json.dumps(request))
        
        LOGGER.info(f"Successfully queued search request: {request_id}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Failed to queue search request: {str(e)}")
        return False

def get_search_result(request_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Get the result of a search request.
    
    Args:
        request_id: The request ID to get results for
        timeout: Timeout in seconds to wait for results
        
    Returns:
        Dictionary containing search results or None if not found
    """
    try:
        client = get_redis_client()
        if not client:
            return None
            
        # Check results queue for matching request_id
        start_time = datetime.now()
        while (datetime.now() - start_time).seconds < timeout:
            # Get all results
            results = client.lrange(RESULTS_QUEUE, 0, -1)
            
            # Check each result for matching request_id
            for result in results:
                data = json.loads(result)
                if data.get('request_id') == request_id:
                    # Remove this result from the queue
                    client.lrem(RESULTS_QUEUE, 1, result)
                    return data
                    
            # Wait a bit before checking again
            time.sleep(0.5)
            
        return None
        
    except Exception as e:
        LOGGER.error(f"Failed to get search result: {str(e)}")
        return None

def store_search_result(request_id: str, results: Dict[str, Any]) -> bool:
    """Store the results of a search request.
    
    Args:
        request_id: The request ID these results are for
        results: Dictionary containing search results
        
    Returns:
        True if storage was successful, False otherwise
    """
    try:
        client = get_redis_client()
        if not client:
            return False
            
        # Prepare result data
        data = {
            'request_id': request_id,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add to results queue
        client.lpush(RESULTS_QUEUE, json.dumps(data))
        
        LOGGER.info(f"Successfully stored search results for request: {request_id}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Failed to store search results: {str(e)}")
        return False

def store_processed_url(url: str) -> bool:
    """Store a processed URL in Redis.
    
    Args:
        url: The URL to store

    Returns:
        True if storage was successful, False otherwise
    """
    try:
        client = get_redis_client()
        if not client:
            return False
            
        # Add URL to set
        client.sadd(PROCESSED_URLS, url)
        
        LOGGER.info(f"Successfully stored processed URL: {url}")
        return True
    except Exception as e:
        LOGGER.error(f"Failed to store processed URL: {str(e)}")
        return False

def is_url_processed(url: str) -> bool:
    """Check if a URL has already been processed.
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL has been processed, False otherwise
    """
    try:
        client = get_redis_client()
        if not client:
            return False
            
        # Check if URL is in the set
        return client.sismember(PROCESSED_URLS, url)
    except Exception as e:
        LOGGER.error(f"Failed to check if URL is processed: {str(e)}")
        return False