import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
"""
Test cases for UserProfileView and UserRegistrationView API endpoints.

This module contains the following tests:

1. User Profile Management:
    - Retrieving user profiles (GET /authentication/api/v1/user-profile/).
    - Updating user profiles (PUT /authentication/api/v1/user-profile/).
    - Partial updates (PUT with format='json').
    - Handling missing profiles (404).
    - Enforcing authentication (401).

2. User Registration:
    - Registering a new user (POST /authentication/api/v1/register/).
    - Handling missing fields (400).
    - Handling password mismatch (400).
    - Upgrading a guest user (POST with authenticated guest).
    - Preventing upgrade of regular users (400).

Author: Your Name
Date: YYYY-MM-DD
"""

from typing import Dict, Any

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from authentication.models import UserProfile
from authentication.v1.signals import create_profile_verification, send_password_reset_email

User = get_user_model()


class UserProfileViewTestCase(TestCase):
    """
    Test cases for the UserProfileView API endpoints.
    """

    def setUp(self) -> None:
        """
        Set up test data and disable unwanted signals.
        """
        # Prevent sending emails or creating verifications during tests
        post_save.disconnect(create_profile_verification, sender=User)
        post_save.disconnect(send_password_reset_email, sender=User)

        self.client = APIClient()
        # Create a user; this will trigger create_or_update_user_profile automatically
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            is_guest=False,
            active=True,
        )
        # Assign initial preferences on the auto-created profile
        self.profile = self.user.profile
        self.profile.preferences = {"category": "electronics"}
        self.profile.save()

        # Authenticate for protected endpoints
        self.client.force_authenticate(user=self.user)

    def tearDown(self) -> None:
        """
        Reconnect signals after tests.
        """
        post_save.connect(create_profile_verification, sender=User)
        post_save.connect(send_password_reset_email, sender=User)

    def test_get_user_profile_success(self) -> None:
        """
        Ensure that the authenticated user can retrieve their profile.
        """
        response = self.client.get("/authentication/api/v1/user-profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], {"category": "electronics"})

    def test_get_user_profile_not_found(self) -> None:
        """
        Ensure that the view returns 404 if a user profile does not exist.
        """
        # Delete the profile
        self.profile.delete()
        response = self.client.get("/authentication/api/v1/user-profile/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
       
    def test_update_user_profile_success(self) -> None:
        """
        Ensure that the user can update their profile successfully.
        """
        data: Dict[str, Any] = {"preferences": {"category": "fashion"}}
        response = self.client.put(
            "/authentication/api/v1/user-profile/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], {"category": "fashion"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.preferences, {"category": "fashion"})

    def test_update_user_profile_partial(self) -> None:
        """
        Send a partial update (e.g., only preferences).
        """
        initial = {"preferences": {"category": "books"}}
        self.client.put(
            "/authentication/api/v1/user-profile/", initial, format="json"
        )
        partial = {"preferences": {"category": "movies"}}
        response = self.client.put(
            "/authentication/api/v1/user-profile/", partial, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], {"category": "movies"})

    def test_update_user_profile_validation_error(self) -> None:
        """
        Send invalid data and expect validation error.
        """
        data: Dict[str, Any] = {"preferences": "invalid_format"}  # should be dict
        response = self.client.put(
            "/authentication/api/v1/user-profile/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_profile_unauthenticated(self) -> None:
        """
        Ensure that unauthenticated users cannot update a profile.
        """
        self.client.force_authenticate(user=None)
        data: Dict[str, Any] = {"preferences": {"category": "books"}}
        response = self.client.put(
            "/authentication/api/v1/user-profile/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserRegistrationViewTestCase(TestCase):
    """
    Test cases for the UserRegistrationView API endpoints.
    """

    def setUp(self) -> None:
        """
        Set up test data and disable unwanted signals.
        """
        post_save.disconnect(create_profile_verification, sender=User)
        post_save.disconnect(send_password_reset_email, sender=User)

        self.client = APIClient()
        # Create a guest user for upgrade tests
        self.guest_user = User.objects.create_user(
            username="guestuser",
            email="guest@example.com",
            password="password123",
            is_guest=True,
        )

    def tearDown(self) -> None:
        """
        Reconnect signals after tests.
        """
        post_save.connect(create_profile_verification, sender=User)
        post_save.connect(send_password_reset_email, sender=User)

    def test_register_new_user_missing_fields(self) -> None:
        """
        Test registering a new user with missing required fields.
        """
        data = {"email": "new@example.com"}  # missing password/confirm
        response = self.client.post(
            "/authentication/api/v1/register/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_register_new_user_password_mismatch(self) -> None:
        """
        Test registering a new user with mismatched passwords.
        """
        data = {
            "email": "new@example.com",
            "password": "pass1",
            "confirm_password": "pass2",
        }
        response = self.client.post(
            "/authentication/api/v1/register/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Passwords do not match.")

    def test_register_new_user_success(self) -> None:
        """
        Test registering a new user with valid data.
        """
        data = {
            "email": "new@example.com",
            "password": "securepass",
            "confirm_password": "securepass",
        }
        response = self.client.post(
            "/authentication/api/v1/register/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User registered successfully.")

    def test_upgrade_guest_user_password_mismatch(self) -> None:
        """
        Test upgrading a guest user with mismatched passwords.
        """
        self.client.force_authenticate(user=self.guest_user)
        data = {"password": "pass1", "confirm_password": "pass2"}
        response = self.client.post(
            "/authentication/api/v1/register/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Passwords do not match.")

    def test_upgrade_guest_user_success(self) -> None:
        """
        Test upgrading a guest user to a regular user.
        """
        self.client.force_authenticate(user=self.guest_user)
        data = {"password": "newpass", "confirm_password": "newpass"}
        response = self.client.post(
            "/authentication/api/v1/register/", data, format="json"
        )
        self.guest_user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(self.guest_user.is_guest)
        self.assertEqual(
            response.data["message"], "Guest user upgraded to a regular user."
        )

    def test_upgrade_registered_user(self) -> None:
        """
        Test attempting to upgrade a registered (non-guest) user.
        """
        reg = User.objects.create_user(
            username="reguser",
            email="reg@example.com",
            password="pass123",
            is_guest=False,
        )
        self.client.force_authenticate(user=reg)
        response = self.client.post(
            "/authentication/api/v1/register/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "You are already registered.")
