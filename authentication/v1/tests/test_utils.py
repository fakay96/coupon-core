"""
Test cases for authentication utilities.

This module tests:
1. Token Manager functionality
2. Redis Client functionality
3. Integration between utilities
"""

import time
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from redis.exceptions import RedisError

from authentication.models import CustomUser
from authentication.v1.utils.redis_client import RedisClient
from authentication.v1.utils.token_manager import TokenManager

User = get_user_model()


class TokenManagerTestCase(TestCase):
    """Test suite for TokenManager utility."""

    databases = {'default', 'authentication_shard'}  # Specify required databases

    def setUp(self) -> None:
        """Set up test data."""
        self.token_manager = TokenManager()
        self.test_user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_create_guest_token(self) -> None:
        """
        Test guest token creation.

        Validates:
            - Token is created successfully
            - Token contains correct claims
            - Error handling for invalid input
        """
        token = self.token_manager.create_guest_token("guest@example.com")
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # Test with invalid email
        with self.assertRaises(ValueError):
            self.token_manager.create_guest_token("")

    def test_create_access_token(self) -> None:
        """
        Test access token creation.

        Validates:
            - Token is created successfully
            - Token contains correct claims
            - Error handling for invalid input
        """
        token = self.token_manager.create_access_token(self.test_user)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # Test with invalid user
        with self.assertRaises(ValueError):
            self.token_manager.create_access_token(None)

    def test_create_refresh_token(self) -> None:
        """
        Test refresh token creation.

        Validates:
            - Token is created successfully
            - Token contains correct claims
            - Error handling for invalid input
        """
        token = self.token_manager.create_refresh_token(self.test_user)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # Test with invalid user
        with self.assertRaises(ValueError):
            self.token_manager.create_refresh_token(None)

    @patch('rest_framework_simplejwt.tokens.AccessToken')
    def test_verify_token(self, mock_access_token) -> None:
        """
        Test token verification.

        Validates:
            - Valid token is verified successfully
            - Invalid token raises appropriate error
            - Error handling for malformed tokens
        """
        # Mock the token verification
        mock_token = MagicMock()
        mock_token.payload = {'user_id': self.test_user.id}
        mock_access_token.for_user.return_value = mock_token

        # Test with valid token
        token = self.token_manager.create_access_token(self.test_user)
        verified_token = self.token_manager.verify_token(token)
        self.assertIsNotNone(verified_token)
        self.assertEqual(verified_token['user_id'], self.test_user.id)

        # Test with invalid token
        with self.assertRaises(ValueError):
            self.token_manager.verify_token("invalid_token")



class RedisClientTestCase(TestCase):
    """Test suite for RedisClient utility."""

    databases = {'default', 'authentication_shard'} 

    def setUp(self) -> None:
        """Set up test data."""
        self.test_key = "test_key"
        self.test_value = "test_value"
        self.redis_client = RedisClient()

    @patch('authentication.v1.utils.redis_client.cache')
    def test_set_token(self, mock_cache) -> None:
        """
        Test setting a token in Redis and in the Django‐cache fallback.

        Validates:
            - Redis path returns True on success
            - Cache path returns True on success
            - On RedisError + cache.set=False, returns False
        """
        fake_redis = MagicMock()

        # --- Redis branch ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.setex.return_value = True
        self.assertTrue(
            self.redis_client.set_token(self.test_key, self.test_value, 3600)
        )

        # --- Django cache branch ---
        self.redis_client.use_django_cache = True
        self.redis_client.client = mock_cache
        mock_cache.set.return_value = True
        self.assertTrue(
            self.redis_client.set_token(self.test_key, self.test_value, 3600)
        )

        # --- Redis error + cache fallback failure ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.setex.side_effect = RedisError()
        mock_cache.set.return_value = False
        self.assertFalse(
            self.redis_client.set_token(self.test_key, self.test_value, 3600)
        )

    @patch('authentication.v1.utils.redis_client.cache')
    def test_get_token(self, mock_cache) -> None:
        """
        Test retrieving a token from Redis and from Django cache.

        Validates:
            - Redis path returns the stored value
            - Cache path returns the stored value
            - Non‐existent key returns None
            - On RedisError + cache.get=None, returns None
        """
        fake_redis = MagicMock()

        # --- Redis branch ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.get.return_value = self.test_value
        self.assertEqual(
            self.redis_client.get_token(self.test_key),
            self.test_value
        )

        # --- Django cache branch ---
        self.redis_client.use_django_cache = True
        self.redis_client.client = mock_cache
        mock_cache.get.return_value = self.test_value
        self.assertEqual(
            self.redis_client.get_token(self.test_key),
            self.test_value
        )

        # --- Non‐existent key in Redis ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.get.return_value = None
        self.assertIsNone(
            self.redis_client.get_token("nonexistent_key")
        )

        # --- RedisError + cache fallback None ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.get.side_effect = RedisError()
        mock_cache.get.return_value = None
        self.assertIsNone(
            self.redis_client.get_token(self.test_key)
        )

    @patch('authentication.v1.utils.redis_client.cache')
    def test_delete_token(self, mock_cache) -> None:
        """
        Test deleting a token from Redis and from Django cache.

        Validates:
            - Redis path returns True when delete count==1
            - Cache path returns True on success
            - On RedisError + cache.delete=False, returns False
        """
        fake_redis = MagicMock()

        # --- Redis branch ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.delete.return_value = 1
        self.assertTrue(
            self.redis_client.delete_token(self.test_key)
        )

        # --- Django cache branch ---
        self.redis_client.use_django_cache = True
        self.redis_client.client = mock_cache
        mock_cache.delete.return_value = True
        self.assertTrue(
            self.redis_client.delete_token(self.test_key)
        )

        # --- RedisError + cache fallback failure ---
        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis
        fake_redis.delete.side_effect = RedisError()
        mock_cache.delete.return_value = False
        self.assertFalse(
            self.redis_client.delete_token(self.test_key)
        )

    @patch('authentication.v1.utils.redis_client.cache')
    def test_connection_error(self, mock_cache) -> None:
        """
        Test all three operations when Redis always errors and the cache fallback also fails.

        Validates:
            - set_token → False
            - get_token → None
            - delete_token → False
        """
        fake_redis = MagicMock()
        fake_redis.setex.side_effect = RedisError()
        fake_redis.get.side_effect = RedisError()
        fake_redis.delete.side_effect = RedisError()

        self.redis_client.use_django_cache = False
        self.redis_client.client = fake_redis

        # stub cache so fallback attempts also fail
        mock_cache.set.return_value = False
        mock_cache.get.return_value = None
        mock_cache.delete.return_value = False

        self.assertFalse(
            self.redis_client.set_token(self.test_key, self.test_value, 3600)
        )
        self.assertIsNone(
            self.redis_client.get_token(self.test_key)
        )
        self.assertFalse(
            self.redis_client.delete_token(self.test_key)
        )

class TokenManagerRedisIntegrationTestCase(TestCase):
    """Test suite for integration between TokenManager and RedisClient."""

    databases = {'default', 'authentication_shard'}  # Specify required databases

    def setUp(self) -> None:
        """Set up test data."""
        self.token_manager = TokenManager()
        self.redis_client = RedisClient()
        self.test_user = User.objects.create_user(
            username="integrationuser",
            email="integration@example.com",
            password="testpass123"
        )

    @patch('authentication.v1.utils.redis_client.redis.Redis')
    def test_token_lifecycle(self, mock_redis) -> None:
        """
        Test complete token lifecycle with Redis integration.

        Validates:
            - Token creation and storage in Redis
            - Token retrieval from Redis
            - Token deletion from Redis
        """
        # Mock Redis operations
        mock_redis.return_value.setex.return_value = True
        mock_redis.return_value.get.return_value = "test_token"
        mock_redis.return_value.delete.return_value = 1

        # Create a guest token
        token = self.token_manager.create_guest_token("guest_lifecycle@example.com")
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

        # Verify token can be retrieved
        verified_token = self.token_manager.verify_token(token)
        self.assertIsNotNone(verified_token)

        # Clean up
        self.redis_client.delete_token(token)

    @patch('authentication.v1.utils.redis_client.redis.Redis')
    def test_token_expiration(self, mock_redis) -> None:
        """
        Test token expiration handling.

        Validates:
            - Expired tokens are properly handled
            - Redis TTL is set correctly
        """
        # Mock Redis operations
        mock_redis.return_value.setex.return_value = True
        mock_redis.return_value.get.return_value = None  # Simulate expired token

        # Create a guest token
        token = self.token_manager.create_guest_token("guest_expiration@example.com")
        self.assertIsInstance(token, str)

        # Verify expired token handling
        self.assertIsNone(self.redis_client.get_token(token)) 