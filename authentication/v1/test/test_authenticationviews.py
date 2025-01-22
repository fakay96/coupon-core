"""
Test suite for authentication views, including guest token creation and retrieval.

This module includes tests to ensure proper handling of guest token functionality with
valid inputs, invalid inputs, and edge cases.
"""

from unittest.mock import ANY, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


class GuestTokenTestCase(APITestCase):
    """
    Test suite for the guest token creation and retrieval functionality.
    """

    def setUp(self):
        """
        Setup the test environment by initializing the API client.
        """
        self.client = APIClient()
        self.guest_token_url = reverse("guest-token")

    @patch("authentication.v1.utils.redis_client.RedisClient.get_token")
    @patch("authentication.v1.utils.redis_client.RedisClient.set_token")
    @patch("authentication.v1.utils.token_manager.TokenManager.create_guest_token")
    def test_guest_token_successful(
        self, mock_create_token, mock_set_token, mock_get_token
    ):
        """
        Test successful guest token creation and retrieval.

        Validates that a guest token is created
        and stored in Redis or an existing token is returned.
        """
        mock_get_token.return_value = None
        mock_create_token.return_value = "guest_token"

        data = {"email": "guest@example.com"}
        response = self.client.post(self.guest_token_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["guest_token"], "guest_token")
        mock_set_token.assert_called_once_with(
            "guest@example.com", "guest_token", ANY)

    @patch("authentication.v1.utils.redis_client.RedisClient.get_token")
    def test_guest_token_existing(self, mock_get_token):
        """
        Test retrieval of an existing guest token from Redis.

        Validates that an existing token is returned without creating a new one.
        """
        mock_get_token.return_value = "existing_token"

        data = {"email": "guest@example.com"}
        response = self.client.post(self.guest_token_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["guest_token"], "existing_token")

    def test_guest_token_invalid_email(self):
        """
        Test guest token creation with an invalid email.

        Ensures the API returns a 400 Bad Request with validation errors.
        """
        data = {"email": "invalid-email"}
        response = self.client.post(self.guest_token_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_guest_token_missing_email(self):
        """
        Test guest token creation with missing email.

        Ensures the API returns a 400 Bad Request with validation errors.
        """
        response = self.client.post(self.guest_token_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
