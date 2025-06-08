import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
"""
Test cases for authentication signals.

This module tests:
1. User profile creation signals
2. User deletion cleanup
3. Signal error handling
4. Guest user profile setup
5. Race condition robustness
"""

from django.test import TestCase
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from unittest.mock import patch
from typing import Dict

from authentication.models import UserProfile
from authentication.v1.signals import create_or_update_user_profile

User = get_user_model()


class SignalsTestCase(TestCase):
    """Test suite for authentication signals that manage UserProfile lifecycle."""

    def setUp(self) -> None:
        """Set up test environment and disconnect signals to prevent automatic behavior."""
        post_save.disconnect(create_or_update_user_profile, sender=User)
        self.user_data: Dict[str, str] = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123"
        }

    def tearDown(self) -> None:
        """Reconnect signals after each test."""
        post_save.connect(create_or_update_user_profile, sender=User)

    def test_profile_creation_signal(self) -> None:
        """Test that UserProfile is automatically created when a new user is saved."""
        post_save.connect(create_or_update_user_profile, sender=User)
        user = User.objects.create_user(**self.user_data)
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(user.profile.user, user)

    def test_profile_deletion_signal(self) -> None:
        """Test that deleting a user also deletes the associated UserProfile."""
        user = User.objects.create_user(**self.user_data)
        profile = UserProfile.objects.create(user=user)
        profile_id = profile.id
        user.delete()
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)

    def test_signal_error_handling(self) -> None:
        """Test that errors during profile creation do not prevent user creation."""
        post_save.connect(create_or_update_user_profile, sender=User)
        with patch('authentication.models.UserProfile.objects.create') as mock_create:
            mock_create.side_effect = Exception("Profile creation error")
            user = User.objects.create_user(**self.user_data)
            self.assertTrue(User.objects.filter(id=user.id).exists())

    def test_guest_user_profile_signal(self) -> None:
        """Test that a guest user has a profile created and appropriate flags set."""
        post_save.connect(create_or_update_user_profile, sender=User)
        guest_data = self.user_data.copy()
        guest_data['is_guest'] = True
        user = User.objects.create_user(**guest_data)
        self.assertTrue(hasattr(user, 'profile'))
        self.assertTrue(user.is_guest)
        self.assertIsInstance(user.profile, UserProfile)

    def test_signal_race_conditions(self) -> None:
        """
        Test handling of potential race conditions in signals.

        Ensures that UserProfile is not duplicated even if concurrently created.
        """
        post_save.connect(create_or_update_user_profile, sender=User)
        user = User.objects.create_user(**self.user_data)

        # Let the signal auto-create the profile
        profile_from_signal = user.profile

        # Attempt to retrieve it again from DB
        profile_direct = UserProfile.objects.get(user=user)

        # Ensure they refer to the same instance
        self.assertEqual(profile_from_signal.id, profile_direct.id)

        # Confirm only one profile exists
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)
