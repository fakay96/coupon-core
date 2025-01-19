"""
Test suite for the admin-related views in the authentication app.

Includes tests for login, registration, and retrieval of user metadata to ensure views handle
valid inputs, invalid inputs, and edge cases appropriately.
"""

from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import CustomUser


class AdminViewsTestCase(APITestCase):
    """
    Test suite for the admin-related views in the authentication app.

    Includes tests for:
    - Admin login functionality.
    - Admin registration.
    - Retrieving user metadata.
    """

    def setUp(self):
        """
        Setup the test environment by creating an admin user and initializing API client.

        The admin user is used for authenticated requests and login tests.
        """
        self.client = APIClient()
        self.login_url = reverse("login")
        self.register_url = reverse("register")
        self.user_info_url = reverse("user-info")

        # Create an admin user
        self.admin_user = CustomUser.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="password123",
            is_staff=True,
        )

    @patch("authentication.v1.utils.token_manager.TokenManager.create_admin_tokens")
    def test_login_successful(self, mock_create_tokens):
        """
        Test successful login for an admin user.

        Validates that the correct tokens (access and refresh) are returned.
        """
        mock_create_tokens.return_value = {
            "access": "access_token",
            "refresh": "refresh_token",
        }

        data = {"username": self.admin_user.username, "password": "password123"}
        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_credentials(self):
        """
        Test login with invalid credentials.

        Ensures the API returns a 400 Bad Request with appropriate error messages.
        """
        data = {"username": "wrong_user", "password": "wrong_password"}
        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_login_missing_data(self):
        """
        Test login with missing username and password.

        Ensures the API returns a 400 Bad Request with validation errors for missing fields.
        """
        response = self.client.post(self.login_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)

    def test_register_successful(self):
        """
        Test successful registration of a new admin user.

        Validates that the API returns a 201 Created status and a success message.
        """
        data = {
            "username": "new_user",
            "email": "new_user@example.com",
            "password": "securepassword",
        }
        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User created successfully")

    def test_register_duplicate_user(self):
        """
        Test registration with a duplicate username.

        Ensures the API returns a 400 Bad Request with an appropriate error message.
        """
        data = {
            "username": self.admin_user.username,
            "email": "duplicate@example.com",
            "password": "password123",
        }
        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_register_missing_data(self):
        """
        Test registration with missing fields.

        Ensures the API returns a 400 Bad Request with validation errors for missing data.
        """
        response = self.client.post(self.register_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)

    def test_user_info_successful(self):
        """
        Test successful retrieval of user metadata for an authenticated admin user.

        Validates that the returned metadata matches the authenticated user.
        """
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.admin_user.id)
        self.assertEqual(response.data["username"], self.admin_user.username)

    def test_user_info_guest_access_denied(self):
        """
        Test access to user metadata for a guest user.

        Ensures the API returns a 403 Forbidden with an appropriate error message.
        """
        guest_user = CustomUser.objects.create_user(
            username="guest_user",
            email="guest@example.com",
            password="password123",
            is_staff=False,
        )
        guest_user.is_guest = True
        self.client.force_authenticate(user=guest_user)

        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", response.data)

    def test_user_info_unauthenticated(self):
        """
        Test access to user metadata without authentication.

        Ensures the API returns a 401 Unauthorized with a detail message.
        """
        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)
