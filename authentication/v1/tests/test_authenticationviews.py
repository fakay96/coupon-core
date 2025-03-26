"""
Test cases for authentication views including login, token refresh, and verification.

This module tests:
1. User login with various scenarios
2. Token refresh functionality
3. Token verification
4. Edge cases and error handling
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

CustomUser = get_user_model()

class AuthenticationViewsTestCase(APITestCase):
    """Test suite for authentication views."""

    def setUp(self) -> None:
        """Set up test data."""
        self.client = APIClient()
        # Create a regular user
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_active=True
        )
        # Create a guest user
        self.guest_user = CustomUser.objects.create_user(
            username="guestuser",
            email="guest@example.com",
            password="guestpass123",
            is_guest=True
        )
        # Create an inactive user
        self.inactive_user = CustomUser.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="inactive123",
            is_active=False
        )

    def test_login_success(self) -> None:
        """
        Test successful login with valid credentials.

        Expected:
            - Returns HTTP 200
            - Returns access and refresh tokens
            - Returns user data
        """
        data = {
            "username": "testuser",
            "password": "password123"
        }
        response = self.client.post("/authentication/api/v1/login/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_login_invalid_credentials(self) -> None:
        """
        Test login with invalid credentials.

        Expected:
            - Returns HTTP 400
            - Returns error message
        """
        data = {
            "username": "testuser",
            "password": "wrongpassword"
        }
        response = self.client.post("/authentication/api/v1/login/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid username or password", str(response.data))

    def test_login_guest_user(self) -> None:
        """
        Test login attempt with guest user credentials.

        Expected:
            - Returns HTTP 400
            - Returns error about guest accounts
        """
        data = {
            "username": "guestuser",
            "password": "guestpass123"
        }
        response = self.client.post("/authentication/api/v1/login/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Guest accounts are not allowed to log in", str(response.data))

    def test_login_inactive_user(self) -> None:
        """
        Test login attempt with inactive user credentials.

        Expected:
            - Returns HTTP 400
            - Returns error about inactive account
        """
        data = {
            "username": "inactive",
            "password": "inactive123"
        }
        response = self.client.post("/authentication/api/v1/login/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("account is not active", str(response.data).lower())

    def test_token_refresh(self) -> None:
        """
        Test refreshing an access token using a valid refresh token.

        Expected:
            - Returns HTTP 200
            - Returns new access token
        """
        # Get initial tokens
        refresh = RefreshToken.for_user(self.user)
        data = {"refresh": str(refresh)}
        response = self.client.post("/authentication/api/v1/token/refresh/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_token_refresh_invalid(self) -> None:
        """
        Test refreshing an access token using an invalid refresh token.

        Expected:
            - Returns HTTP 401
            - Returns error about invalid token
        """
        data = {"refresh": "invalid_token"}
        response = self.client.post("/authentication/api/v1/token/refresh/", data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_verify(self) -> None:
        """
        Test verifying a valid token.

        Expected:
            - Returns HTTP 200 for valid token
            - Returns HTTP 401 for invalid token
        """
        # Test with valid token
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        response = self.client.post(
            "/authentication/api/v1/token/verify/",
            {"token": access_token}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test with invalid token
        response = self.client.post(
            "/authentication/api/v1/token/verify/",
            {"token": "invalid_token"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self) -> None:
        """
        Test login attempt with missing required fields.

        Expected:
            - Returns HTTP 400
            - Returns error about required fields
        """
        # Missing password
        response = self.client.post(
            "/authentication/api/v1/login/",
            {"username": "testuser"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", str(response.data).lower())

        # Missing username
        response = self.client.post(
            "/authentication/api/v1/login/",
            {"password": "password123"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", str(response.data).lower())

    def test_login_case_sensitivity(self) -> None:
        """
        Test login with different case variations of username.

        Expected:
            - Username should be case-insensitive
            - Returns HTTP 200 for valid credentials regardless of case
        """
        variations = [
            "TESTUSER",
            "testuser",
            "TestUser",
            "testUser"
        ]
        for username in variations:
            data = {
                "username": username,
                "password": "password123"
            }
            response = self.client.post("/authentication/api/v1/login/", data)
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Login failed for username variation: {username}"
            )
