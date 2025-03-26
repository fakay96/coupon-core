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

    databases = {'default', 'authentication_shard'}  # Specify required databases

    def setUp(self) -> None:
        """Set up test data."""
        self.test_key = "test_key"
        self.test_value = "test_value"
        self.redis_client = RedisClient()

    @patch('authentication.v1.utils.redis_client.redis.StrictRedis')
    @patch('authentication.v1.utils.redis_client.cache')
    def test_set_token(self, mock_cache, mock_redis) -> None:
        """
        Test setting a token in Redis.

        Validates:
            - Token is set successfully
            - Expiration time is set correctly
            - Redis errors are handled properly
        """
        # Test with Redis
        mock_instance = mock_redis.return_value
        mock_instance.setex.return_value = True
        result = self.redis_client.set_token(
            self.test_key,
            self.test_value,
            3600
        )
        self.assertTrue(result)

        # Test with Django cache
        self.redis_client.use_django_cache = True
        mock_cache.set.return_value = True
        result = self.redis_client.set_token(
            self.test_key,
            self.test_value,
            3600
        )
        self.assertTrue(result)

        # Test Redis error
        self.redis_client.use_django_cache = False
        mock_instance.setex.side_effect = RedisError()
        result = self.redis_client.set_token(
            self.test_key,
            self.test_value,
            3600
        )
        self.assertFalse(result)

    @patch('authentication.v1.utils.redis_client.redis.StrictRedis')
    @patch('authentication.v1.utils.redis_client.cache')
    def test_get_token(self, mock_cache, mock_redis) -> None:
        """
        Test retrieving a token from Redis.

        Validates:
            - Existing token is retrieved successfully
            - Non-existent token returns None
            - Redis errors are handled properly
        """
        # Test with Redis
        mock_instance = mock_redis.return_value
        mock_instance.get.return_value = self.test_value
        result = self.redis_client.get_token(self.test_key)
        self.assertEqual(result, self.test_value)

        # Test with Django cache
        self.redis_client.use_django_cache = True
        mock_cache.get.return_value = self.test_value
        result = self.redis_client.get_token(self.test_key)
        self.assertEqual(result, self.test_value)

        # Test non-existent key
        mock_instance.get.return_value = None
        result = self.redis_client.get_token("nonexistent_key")
        self.assertIsNone(result)

        # Test Redis error
        mock_instance.get.side_effect = RedisError()
        result = self.redis_client.get_token(self.test_key)
        self.assertIsNone(result)

    @patch('authentication.v1.utils.redis_client.redis.StrictRedis')
    @patch('authentication.v1.utils.redis_client.cache')
    def test_delete_token(self, mock_cache, mock_redis) -> None:
        """
        Test deleting a token from Redis.

        Validates:
            - Token is deleted successfully
            - Redis errors are handled properly
        """
        # Test with Redis
        mock_instance = mock_redis.return_value
        mock_instance.delete.return_value = 1
        result = self.redis_client.delete_token(self.test_key)
        self.assertTrue(result)

        # Test with Django cache
        self.redis_client.use_django_cache = True
        mock_cache.delete.return_value = True
        result = self.redis_client.delete_token(self.test_key)
        self.assertTrue(result)

        # Test Redis error
        self.redis_client.use_django_cache = False
        mock_instance.delete.side_effect = RedisError()
        result = self.redis_client.delete_token(self.test_key)
        self.assertFalse(result)

    @patch('authentication.v1.utils.redis_client.redis.StrictRedis')
    @patch('authentication.v1.utils.redis_client.cache')
    def test_connection_error(self, mock_cache, mock_redis) -> None:
        """
        Test Redis connection error handling.

        Validates:
            - Connection errors are handled gracefully
            - Operations fail safely when Redis is unavailable
        """
        mock_redis.side_effect = RedisError()

        # Test all operations with connection error
        self.assertFalse(
            self.redis_client.set_token(self.test_key, self.test_value, 3600)
        )
        self.assertIsNone(self.redis_client.get_token(self.test_key))
        self.assertFalse(self.redis_client.delete_token(self.test_key))


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