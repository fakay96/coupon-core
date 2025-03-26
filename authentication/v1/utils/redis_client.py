"""
Utility module for handling Redis operations.

This module provides a Redis client for setting and retrieving tokens with enhanced
error handling and configurations sourced from Django settings.
"""

from typing import Any, Optional

import redis
from django.conf import settings
from django.core.cache import cache


class RedisClient:
    """Handles Redis connections and operations with enhanced error handling."""

    def __init__(self) -> None:
        """
        Initialize the Redis client with configuration from Django settings.

        The client will use Django's cache backend for testing and Redis for production.
        """
        self.use_django_cache = True
        self.client = cache

        try:
            cache_backend = settings.CACHES['default']['BACKEND']
            if 'LocMemCache' not in cache_backend:
                # Use Redis for production
                self.use_django_cache = False
                cache_location = settings.CACHES['default']['LOCATION']
                if '://' in cache_location:
                    # Parse Redis URL format (redis://host:port/db)
                    host = cache_location.split('://')[1].split(':')[0]
                    port = int(cache_location.split(':')[2].split('/')[0])
                else:
                    # Use direct host value
                    host = cache_location
                    port = 6379

                self.client = redis.StrictRedis(
                    host=host,
                    port=port,
                    password='redis_password',
                    decode_responses=True,
                )
                # Test connection
                self.client.ping()
        except (redis.ConnectionError, Exception):
            # Keep using Django's cache as fallback
            self.use_django_cache = True
            self.client = cache

    def set_token(self, key: str, value: Any, expiry: int) -> bool:
        """
        Store a token in Redis with a specified expiration.

        Args:
            key (str): The key under which the token will be stored.
            value (Any): The token value to store.
            expiry (int): The time-to-live (TTL) for the token in seconds.

        Returns:
            bool: True if the token was set successfully, False otherwise.
        """
        try:
            if self.use_django_cache:
                return bool(self.client.set(key, value, timeout=expiry))
            else:
                return bool(self.client.setex(key, expiry, value))
        except (redis.RedisError, Exception):
            # Fallback to Django cache on Redis error
            self.use_django_cache = True
            self.client = cache
            try:
                return bool(self.client.set(key, value, timeout=expiry))
            except Exception:
                return False

    def get_token(self, key: str) -> Optional[str]:
        """
        Retrieve a token from Redis.

        Args:
            key (str): The key of the token to retrieve.

        Returns:
            Optional[str]: The token value if found, or None if the key does not exist
            or if there was an error.
        """
        try:
            if self.use_django_cache:
                value = self.client.get(key)
            else:
                value = self.client.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                return value.decode('utf-8')
            return str(value)
        except (redis.RedisError, Exception):
            # Fallback to Django cache on Redis error
            self.use_django_cache = True
            self.client = cache
            try:
                value = self.client.get(key)
                return str(value) if value is not None else None
            except Exception:
                return None

    def delete_token(self, key: str) -> bool:
        """
        Delete a token from Redis.

        Args:
            key (str): The key of the token to delete.

        Returns:
            bool: True if the token was deleted successfully, False otherwise.
        """
        try:
            if self.use_django_cache:
                return bool(self.client.delete(key))
            else:
                return bool(self.client.delete(key))
        except (redis.RedisError, Exception):
            # Fallback to Django cache on Redis error
            self.use_django_cache = True
            self.client = cache
            try:
                return bool(self.client.delete(key))
            except Exception:
                return False
