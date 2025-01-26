"""
Test cases for UserProfileView and UserRegistrationView API endpoints.

This module contains the following tests:
1. User Profile Management:
    - Test retrieving user profiles (GET /authentication/api/v1/user-profile/).
    - Test updating user profiles (PUT /authentication/api/v1/user-profile/).

2. User Registration:
    - Test registering a new user (POST /authentication/api/v1/register/).
    - Test upgrading a guest user to a regular user (POST /authentication/api/v1/register/).

Author: Your Name
Date: YYYY-MM-DD
"""

from typing import Dict

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from authentication.models import CustomUser, UserProfile


class UserProfileViewTestCase(APITestCase):
    """
    Test cases for the UserProfileView API endpoints.

    Includes tests for retrieving and updating user profiles.
    """

    def setUp(self) -> None:
        """
        Set up test data for user profile management tests.
        """
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            preferences={"category": "electronics"},
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_user_profile_success(self) -> None:
        """
        Test retrieving the profile of an authenticated user.

        Expected Behavior:
            - Returns HTTP 200 with profile details.
        """
        response = self.client.get("/authentication/api/v1/user-profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], {"category": "electronics"})

    def test_get_user_profile_not_found(self) -> None:
        """
        Test retrieving the profile of a user without an associated profile.

        Expected Behavior:
            - Returns HTTP 404 with an error message.
        """
        self.profile.delete()
        response = self.client.get("/authentication/api/v1/user-profile/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Profile not found.")

    def test_update_user_profile_success(self) -> None:
        """
        Test updating the profile of an authenticated user.

        Expected Behavior:
            - Returns HTTP 200 with updated profile details.
        """
        data: Dict[str, Dict[str, str]] = {"preferences": {"category": "fashion"}}
        response = self.client.put("/authentication/api/v1/user-profile/", data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], {"category": "fashion"})

    def test_update_user_profile_validation_error(self) -> None:
        """
        Test updating the profile with invalid data.

        Expected Behavior:
            - Returns HTTP 400 with validation error details.
        """
        data: Dict[str, str] = {"preferences": "invalid_format"}  # Invalid type
        response = self.client.put("/authentication/api/v1/user-profile/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserRegistrationViewTestCase(APITestCase):
    """
    Test cases for the UserRegistrationView API endpoints.

    Includes tests for registering new users and upgrading guest users.
    """

    def setUp(self) -> None:
        """
        Set up test data for user registration tests.
        """
        self.guest_user = CustomUser.objects.create_user(
            username="guestuser",
            email="guest@example.com",
            password="password123",
            is_guest=True,
        )
        self.client = APIClient()

    def test_register_new_user_success(self) -> None:
        """
        Test registering a new user with valid data.

        Expected Behavior:
            - Returns HTTP 201 with a success message and user details.
        """
        data: Dict[str, str] = {
            "email": "newuser@example.com",
            "password": "password123",
            "confirm_password": "password123",
        }
        response = self.client.post("/authentication/api/v1/register/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User registered successfully.")

    def test_register_new_user_password_mismatch(self) -> None:
        """
        Test registering a new user with mismatched passwords.

        Expected Behavior:
            - Returns HTTP 400 with an error message.
        """
        data: Dict[str, str] = {
            "email": "newuser@example.com",
            "password": "password123",
            "confirm_password": "password321",
        }
        response = self.client.post("/authentication/api/v1/register/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"], "Password and confirm password do not match."
        )

    def test_register_new_user_missing_fields(self) -> None:
        """
        Test registering a new user with missing required fields.

        Expected Behavior:
            - Returns HTTP 400 with an error message.
        """
        data: Dict[str, str] = {
            "email": "newuser@example.com"
        }  # Missing password fields
        response = self.client.post("/authentication/api/v1/register/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"],
            "Email, password, and confirm password are required.",
        )

    def test_upgrade_guest_user_success(self) -> None:
        """
        Test upgrading a guest user to a regular user.

        Expected Behavior:
            - Returns HTTP 201 with a success message.
            - The user's `is_guest` flag is set to False.
        """
        self.client.force_authenticate(user=self.guest_user)
        data: Dict[str, str] = {
            "password": "newsecurepassword",
            "confirm_password": "newsecurepassword",
        }
        response = self.client.post("/authentication/api/v1/register/", data)
        self.guest_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(self.guest_user.is_guest)
        self.assertEqual(
            response.data["message"], "Guest user upgraded to a regular user."
        )

    def test_upgrade_guest_user_password_mismatch(self) -> None:
        """
        Test upgrading a guest user with mismatched passwords.

        Expected Behavior:
            - Returns HTTP 400 with an error message.
        """
        self.client.force_authenticate(user=self.guest_user)
        data: Dict[str, str] = {
            "password": "password123",
            "confirm_password": "password321",
        }
        response = self.client.post("/authentication/api/v1/register/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error"], "Password and confirm password do not match."
        )

    def test_upgrade_registered_user(self) -> None:
        """
        Test attempting to upgrade a registered (non-guest) user.

        Expected Behavior:
            - Returns HTTP 400 with an error message.
        """
        registered_user = CustomUser.objects.create_user(
            username="registereduser",
            email="registered@example.com",
            password="password123",
            is_guest=False,
        )
        self.client.force_authenticate(user=registered_user)
        response = self.client.post("/authentication/api/v1/register/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "You are already registered.")
