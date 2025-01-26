"""
Utility module for Redis operations specific to geodiscounts.

Extends RedisClient functionality for discount-specific use cases.
"""

import json

from authentication.v1.utils.redis_client import RedisClient

redis_client = RedisClient()


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
