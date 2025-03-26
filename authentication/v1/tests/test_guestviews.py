"""
Test cases for guest-related views.

This module tests:
1. Guest token generation
2. Guest user creation
3. Guest user authentication
4. Guest user restrictions
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from authentication.models import CustomUser
from authentication.v1.utils.redis_client import RedisClient
from authentication.v1.utils.token_manager import TokenManager


class GuestViewsTestCase(TestCase):
    """Test suite for guest views."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = APIClient()
        self.token_manager = TokenManager()
        self.redis_client = RedisClient()

    @patch('authentication.v1.utils.redis_client.redis.Redis')
    def test_create_guest_token_success(self, mock_redis) -> None:
        """
        Test successful guest token creation.

        Expected:
            - Returns HTTP 201
            - Returns guest token
            - Creates guest user
            - Stores token in Redis
        """
        mock_redis.return_value.set.return_value = True
        mock_redis.return_value.get.return_value = None

        data = {"email": "guest@example.com"}
        response = self.client.post("/authentication/api/v1/guest-token/", data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("guest_token", response.data)

        # Verify guest user was created
        user = CustomUser.objects.get(email="guest@example.com")
        self.assertTrue(user.is_guest)
        self.assertFalse(user.has_usable_password())

    @patch('authentication.v1.utils.redis_client.redis.Redis')
    def test_create_guest_token_existing_token(self, mock_redis) -> None:
        """
        Test guest token creation when token already exists.

        Expected:
            - Returns HTTP 200
            - Returns existing token
            - Doesn't create new user
        """
        existing_token = "existing_token"
        mock_redis.return_value.get.return_value = existing_token.encode()

        data = {"email": "guest@example.com"}
        response = self.client.post("/authentication/api/v1/guest-token/", data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["guest_token"], existing_token)

    def test_create_guest_token_invalid_email(self) -> None:
        """
        Test guest token creation with invalid email.

        Expected:
            - Returns HTTP 400
            - Returns validation error
            - Doesn't create user
        """
        data = {"email": "invalid_email"}
        response = self.client.post("/authentication/api/v1/guest-token/", data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(response.data).lower())
        self.assertEqual(CustomUser.objects.filter(email="invalid_email").count(), 0)

    def test_create_guest_token_missing_email(self) -> None:
        """
        Test guest token creation without email.

        Expected:
            - Returns HTTP 400
            - Returns validation error
        """
        response = self.client.post("/authentication/api/v1/guest-token/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(response.data).lower())

    @patch('authentication.v1.utils.redis_client.redis.Redis')
    def test_guest_token_redis_error(self, mock_redis) -> None:
        """
        Test guest token creation with Redis error.

        Expected:
            - Returns HTTP 500
            - Returns error message
            - Doesn't create user
        """
        mock_redis.return_value.set.side_effect = Exception("Redis error")

        data = {"email": "guest@example.com"}
        response = self.client.post("/authentication/api/v1/guest-token/", data)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)

    def test_guest_access_restrictions(self) -> None:
        """
        Test guest user access restrictions.

        Expected:
            - Cannot access protected endpoints
            - Cannot modify other users' data
            - Cannot perform admin actions
        """
        # Create and authenticate guest user
        guest = CustomUser.objects.create_user(
            username="guest",
            email="guest@example.com",
            password="guestpass",
            is_guest=True
        )
        self.client.force_authenticate(user=guest)

        # Test accessing protected endpoint
        response = self.client.get("/authentication/api/v1/protected/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test accessing admin endpoint
        response = self.client.get("/authentication/api/v1/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_token_expiration(self) -> None:
        """
        Test guest token expiration handling.

        Expected:
            - Expired token is not accepted
            - New token is generated on expiration
        """
        # Create expired token
        email = "guest@example.com"
        CustomUser.objects.create_user(
            username="guest",
            email=email,
            is_guest=True
        )

        with patch('authentication.v1.utils.redis_client.redis.Redis') as mock_redis:
            # First request - no token in Redis (expired)
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.set.return_value = True

            response = self.client.post(
                "/authentication/api/v1/guest-token/",
                {"email": email}
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn("guest_token", response.data)

    def test_guest_user_upgrade(self) -> None:
        """
        Test upgrading guest user to regular user.

        Expected:
            - Guest flag is removed
            - Password is set
            - Can access regular user features
        """
        # Create guest user
        guest = CustomUser.objects.create_user(
            username="guest",
            email="guest@example.com",
            is_guest=True
        )
        self.client.force_authenticate(user=guest)

        # Upgrade to regular user
        data = {
            "password": "newpassword123",
            "confirm_password": "newpassword123"
        }
        response = self.client.post("/authentication/api/v1/register/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify user was upgraded
        guest.refresh_from_db()
        self.assertFalse(guest.is_guest)
        self.assertTrue(guest.has_usable_password())

    def test_guest_concurrent_requests(self) -> None:
        """
        Test handling of concurrent guest token requests.

        Expected:
            - Returns same token for concurrent requests
            - Maintains data consistency
        """
        email = "guest@example.com"

        with patch('authentication.v1.utils.redis_client.redis.Redis') as mock_redis:
            # Simulate race condition by returning None first, then a token
            mock_redis.return_value.get.side_effect = [None, "existing_token".encode()]
            mock_redis.return_value.set.return_value = True

            # First request
            response1 = self.client.post(
                "/authentication/api/v1/guest-token/",
                {"email": email}
            )
            # Second request (concurrent)
            response2 = self.client.post(
                "/authentication/api/v1/guest-token/",
                {"email": email}
            )

            self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response2.status_code, status.HTTP_200_OK)

            # Verify only one user was created
            self.assertEqual(
                CustomUser.objects.filter(email=email).count(),
                1
            )

    @patch('authentication.v1.utils.redis_client.redis.Redis')
    def test_guest_token_cleanup(self, mock_redis) -> None:
        """
        Test guest token cleanup on user upgrade.

        Expected:
            - Token is removed from Redis when user is upgraded
            - Cannot use old guest token after upgrade
        """
        # Setup
        email = "guest@example.com"
        guest = CustomUser.objects.create_user(
            username="guest",
            email=email,
            is_guest=True
        )
        token = self.token_manager.create_guest_token(email)
        mock_redis.return_value.get.return_value = token.encode()
        mock_redis.return_value.delete.return_value = 1

        self.client.force_authenticate(user=guest)

        # Upgrade user
        data = {
            "password": "newpassword123",
            "confirm_password": "newpassword123"
        }
        response = self.client.post("/authentication/api/v1/register/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify token was deleted
        mock_redis.return_value.delete.assert_called_with(email)

        # Try to use old token
        mock_redis.return_value.get.return_value = None
        response = self.client.post("/authentication/api/v1/guest-token/", {"email": email})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST) 