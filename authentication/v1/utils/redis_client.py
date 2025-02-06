"""
Utility module for handling Redis operations.

This module provides a Redis client for setting and retrieving tokens with enhanced
error handling and configurations sourced from Django settings.
"""

from typing import Any, Optional

import redis
from django.conf import settings


class RedisClient:
    """Handles Redis connections and operations with enhanced error handling."""

    def __init__(self) -> None:
        """
        Initialize the Redis client with configuration from Django settings.

        Raises:
            redis.ConnectionError: If the Redis server is unreachable.
        """
        try:
            self.client = redis.StrictRedis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
        except redis.ConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to Redis: {str(e)}"
            ) from e

    def set_token(self, key: str, value: Any, expiry: int) -> None:
        """
        Store a token in Redis with a specified expiration.

        Args:
            key (str): The key under which the token will be stored.
            value (Any): The token value to store.
            expiry (int): The time-to-live (TTL) for the token in seconds.

        Raises:
            redis.RedisError: If the token cannot be set.
        """
        try:
            self.client.setex(key, expiry, value)
        except redis.RedisError as e:
            raise RuntimeError(
                f"Failed to set token for key '{key}': {str(e)}"
            ) from e

    def get_token(self, key: str) -> Optional[str]:
        """
        Retrieve a token from Redis.

        Args:
            key (str): The key of the token to retrieve.

        Returns:
            Optional[str]: The token value if found, or None if the key does not exist.

        Raises:
            redis.RedisError: If the token cannot be retrieved.
        """
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            raise RuntimeError(
                f"Failed to get token for key '{key}': {str(e)}"
            ) from e
