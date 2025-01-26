import unittest
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import TokenError

from authentication.v1.utils.redis_client import RedisClient
from authentication.v1.utils.token_manager import TokenManager

CustomUser = get_user_model()


class TestRedisClient(unittest.TestCase):
    """
    Test cases for the RedisClient utility class.
    """

    @patch("authentication.utils.redis.StrictRedis")
    def setUp(self, mock_redis: MagicMock) -> None:
        """
        Set up the mock Redis client.
        """
        self.mock_redis_instance = mock_redis.return_value
        self.redis_client = RedisClient()

    def test_set_token_success(self) -> None:
        """
        Test setting a token in Redis successfully.
        """
        self.redis_client.set_token("test_key", "test_value", 60)
        self.mock_redis_instance.setex.assert_called_once_with(
            "test_key", 60, "test_value"
        )

    def test_set_token_failure(self) -> None:
        """
        Test handling errors when setting a token in Redis.
        """
        self.mock_redis_instance.setex.side_effect = Exception("Redis error")
        with self.assertRaises(RuntimeError) as context:
            self.redis_client.set_token("test_key", "test_value", 60)
        self.assertIn("Failed to set token for key", str(context.exception))

    def test_get_token_success(self) -> None:
        """
        Test retrieving a token from Redis successfully.
        """
        self.mock_redis_instance.get.return_value = "test_value"
        token: Optional[str] = self.redis_client.get_token("test_key")
        self.mock_redis_instance.get.assert_called_once_with("test_key")
        self.assertEqual(token, "test_value")

    def test_get_token_failure(self) -> None:
        """
        Test handling errors when retrieving a token from Redis.
        """
        self.mock_redis_instance.get.side_effect = Exception("Redis error")
        with self.assertRaises(RuntimeError) as context:
            self.redis_client.get_token("test_key")
        self.assertIn("Failed to get token for key", str(context.exception))


class TestTokenManager(unittest.TestCase):
    """
    Test cases for the TokenManager utility class.
    """

    def setUp(self) -> None:
        """
        Set up test users.
        """
        self.guest_user = CustomUser(
            username="guest", email="guest@example.com", is_guest=True
        )
        self.admin_user = CustomUser(
            username="admin", email="admin@example.com", is_guest=False
        )

    @patch("authentication.utils.token_manager.RefreshToken")
    def test_create_guest_token_success(self, mock_refresh_token: MagicMock) -> None:
        """
        Test generating a token for a guest user successfully.
        """
        mock_refresh_instance = mock_refresh_token.for_user.return_value
        mock_refresh_instance.access_token = "guest_access_token"

        token: str = TokenManager.create_guest_token(self.guest_user)

        mock_refresh_token.for_user.assert_called_once_with(self.guest_user)
        self.assertEqual(token, "guest_access_token")

    @patch("authentication.utils.token_manager.RefreshToken")
    def test_create_guest_token_failure(self, mock_refresh_token: MagicMock) -> None:
        """
        Test handling errors when generating a guest token.
        """
        mock_refresh_token.for_user.side_effect = TokenError("Token generation error")

        with self.assertRaises(ValueError) as context:
            TokenManager.create_guest_token(self.guest_user)

        self.assertIn("Unable to generate guest token", str(context.exception))

    @patch("authentication.utils.token_manager.RefreshToken")
    def test_create_admin_tokens_success(self, mock_refresh_token: MagicMock) -> None:
        """
        Test generating tokens (access and refresh) for an admin user successfully.
        """
        mock_refresh_instance = mock_refresh_token.for_user.return_value
        mock_refresh_instance.access_token = "admin_access_token"
        mock_refresh_instance.__str__.return_value = "admin_refresh_token"

        tokens: Dict[str, str] = TokenManager.create_admin_tokens(self.admin_user)

        mock_refresh_token.for_user.assert_called_once_with(self.admin_user)
        self.assertEqual(tokens["access"], "admin_access_token")
        self.assertEqual(tokens["refresh"], "admin_refresh_token")

    @patch("authentication.utils.token_manager.RefreshToken")
    def test_create_admin_tokens_failure(self, mock_refresh_token: MagicMock) -> None:
        """
        Test handling errors when generating tokens for an admin user.
        """
        mock_refresh_token.for_user.side_effect = TokenError("Token generation error")

        with self.assertRaises(ValueError) as context:
            TokenManager.create_admin_tokens(self.admin_user)

        self.assertIn(
            "Unable to generate tokens for the admin user", str(context.exception)
        )
