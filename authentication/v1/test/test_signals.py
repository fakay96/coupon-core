"""
Test cases for UserProfile signal to ensure profiles are created and updated correctly.

This module verifies:
1. UserProfile creation when a new CustomUser is created.
2. UserProfile update when the associated CustomUser is saved.
3. Automatic UserProfile creation if missing for an existing CustomUser.

"""

from typing import Any

from django.test import TestCase

from authentication.models import CustomUser, UserProfile


class UserProfileSignalTestCase(TestCase):
    """
    Test case for the UserProfile signal to ensure profiles are created and updated correctly.
    """

    def test_user_profile_creation_on_user_creation(self) -> None:
        """
        Test that a UserProfile is automatically created when a new CustomUser is created.

        Validates:
            - The `profile` attribute exists on the user instance.
            - The created profile is an instance of `UserProfile`.
            - The `user` field in the profile correctly points to the CustomUser.

        Expected Outcome:
            - A UserProfile instance is created for the CustomUser.
        """
        user: CustomUser = CustomUser.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.assertTrue(hasattr(user, "profile"))  # Verify the profile attribute exists
        self.assertIsInstance(
            user.profile, UserProfile
        )  # Verify the profile is a UserProfile instance
        self.assertEqual(
            user.profile.user, user
        )  # Verify the profile links back to the user

    def test_user_profile_update_on_user_save(self) -> None:
        """
        Test that the UserProfile is updated when the associated CustomUser is saved.

        Validates:
            - The UserProfile remains linked to the CustomUser after an update.
            - The signal does not disrupt the UserProfile-user relationship.

        Expected Outcome:
            - The UserProfile remains intact and linked to the user.
        """
        user: CustomUser = CustomUser.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        user.username = "updateduser"  # Update the username
        user.save()  # Trigger the signal
        self.assertEqual(
            user.profile.user, user
        )  # Ensure the profile is still linked to the user

    def test_user_profile_created_if_missing_for_existing_user(self) -> None:
        """
        Test that a missing UserProfile is automatically created for an existing CustomUser.

        Validates:
            - The `profile` attribute is recreated if missing.
            - The recreated profile is an instance of `UserProfile`.
            - The `user` field in the recreated profile correctly points to the CustomUser.

        Expected Outcome:
            - A new UserProfile is created for the user if it was missing.
        """
        user: CustomUser = CustomUser.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        user.profile.delete()  # Simulate a missing profile by deleting it
        user.save()  # Trigger the signal
        self.assertTrue(
            hasattr(user, "profile")
        )  # Verify the profile attribute exists again
        self.assertIsInstance(
            user.profile, UserProfile
        )  # Verify the recreated profile is a UserProfile instance
        self.assertEqual(
            user.profile.user, user
        )  # Verify the recreated profile links back to the user
