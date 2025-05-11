"""Redis client utilities for the coupon core application.

This module provides Redis client instances for different purposes:
- Celery broker
- Cache
- Geodiscount processing
"""

from typing import Optional
import redis
from django.conf import settings

def get_geodiscount_redis_client() -> redis.Redis:
    """Get a Redis client instance specifically for geodiscount processing.
    
    This client is configured with:
    - Automatic string decoding
    - Connection pooling
    - Error handling
    
    Returns:
        redis.Redis: A configured Redis client instance for geodiscount processing.
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )

def get_celery_redis_client() -> redis.Redis:
    """Get a Redis client instance for Celery broker operations.
    
    Returns:
        redis.Redis: A configured Redis client instance for Celery broker.
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=False,  # Celery needs bytes
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )

def get_cache_redis_client() -> redis.Redis:
    """Get a Redis client instance for caching operations.
    
    Returns:
        redis.Redis: A configured Redis client instance for caching.
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True
    ) 