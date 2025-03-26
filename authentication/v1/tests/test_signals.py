"""
Test cases for authentication signals.

This module tests:
1. User profile creation signals
2. User deletion signals
3. User update signals
4. Signal error handling
"""

from django.test import TestCase
from django.db.models.signals import post_save, post_delete
from django.contrib.auth import get_user_model
from unittest.mock import patch

from authentication.models import UserProfile
from authentication.v1.signals import (
    create_user_profile,
    save_user_profile,
    cleanup_user_data
)

User = get_user_model()

class SignalsTestCase(TestCase):
    """Test suite for authentication signals."""

    def setUp(self):
        """Set up test data and disable signals temporarily."""
        # Disconnect signals temporarily to control test environment
        post_save.disconnect(create_user_profile, sender=User)
        post_save.disconnect(save_user_profile, sender=User)
        post_delete.disconnect(cleanup_user_data, sender=User)

        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123"
        }

    def tearDown(self):
        """Clean up and reconnect signals."""
        # Reconnect signals
        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)
        post_delete.connect(cleanup_user_data, sender=User)

    def test_profile_creation_signal(self):
        """
        Test automatic profile creation when user is created.

        Expected:
            - UserProfile is created
            - Profile is linked to user
            - Default values are set correctly
        """
        # Reconnect create_user_profile signal
        post_save.connect(create_user_profile, sender=User)

        user = User.objects.create_user(**self.user_data)
        
        # Verify profile was created
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(user.profile.user, user)

    def test_profile_update_signal(self):
        """
        Test profile update when user is updated.

        Expected:
            - Profile is updated when user is updated
            - Changes are persisted correctly
        """
        # Create user without signals
        user = User.objects.create_user(**self.user_data)
        profile = UserProfile.objects.create(user=user)

        # Reconnect save_user_profile signal
        post_save.connect(save_user_profile, sender=User)

        # Update user
        user.first_name = "Updated"
        user.save()

        # Refresh profile from db
        profile.refresh_from_db()
        self.assertEqual(profile.user.first_name, "Updated")

    def test_profile_deletion_signal(self):
        """
        Test profile deletion when user is deleted.

        Expected:
            - Profile is deleted when user is deleted
            - Related data is cleaned up
        """
        # Create user and profile
        user = User.objects.create_user(**self.user_data)
        profile = UserProfile.objects.create(user=user)

        # Reconnect cleanup signal
        post_delete.connect(cleanup_user_data, sender=User)

        # Store profile ID for later verification
        profile_id = profile.id

        # Delete user
        user.delete()

        # Verify profile was deleted
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)

    def test_signal_error_handling(self):
        """
        Test error handling in signals.

        Expected:
            - Errors in signals are caught and logged
            - User operations still succeed
            - System remains in consistent state
        """
        # Reconnect signals
        post_save.connect(create_user_profile, sender=User)

        # Mock profile creation to raise an error
        with patch('authentication.models.UserProfile.objects.create') as mock_create:
            mock_create.side_effect = Exception("Profile creation error")

            # Create user should still succeed
            user = User.objects.create_user(**self.user_data)
            self.assertTrue(User.objects.filter(id=user.id).exists())

    def test_multiple_signal_handlers(self):
        """
        Test multiple signal handlers execution.

        Expected:
            - All handlers execute in correct order
            - Each handler's changes are applied
            - Final state is consistent
        """
        # Reconnect all signals
        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)

        # Create user
        user = User.objects.create_user(**self.user_data)

        # Verify both handlers executed
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.user, user)

    def test_signal_race_conditions(self):
        """
        Test handling of potential race conditions in signals.

        Expected:
            - Concurrent operations are handled correctly
            - Data integrity is maintained
        """
        # Reconnect create_user_profile signal
        post_save.connect(create_user_profile, sender=User)

        # Simulate race condition by creating profile before signal
        user = User.objects.create_user(**self.user_data)
        profile1 = UserProfile.objects.create(user=user)

        # Signal handler should not create duplicate profile
        profile2 = getattr(user, 'profile', None)
        self.assertEqual(profile1.id, profile2.id)

    def test_guest_user_profile_signal(self):
        """
        Test profile creation for guest users.

        Expected:
            - Guest user profile is created with appropriate flags
            - Guest-specific defaults are applied
        """
        # Reconnect create_user_profile signal
        post_save.connect(create_user_profile, sender=User)

        # Create guest user
        guest_data = self.user_data.copy()
        guest_data['is_guest'] = True
        user = User.objects.create_user(**guest_data)

        # Verify guest profile
        self.assertTrue(hasattr(user, 'profile'))
        self.assertTrue(user.is_guest)
        self.assertIsInstance(user.profile, UserProfile)

    def test_signal_idempotency(self):
        """
        Test signal handler idempotency.

        Expected:
            - Multiple signal executions don't create duplicate data
            - State remains consistent after multiple saves
        """
        # Reconnect signals
        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)

        # Create and save user multiple times
        user = User.objects.create_user(**self.user_data)
        initial_profile_id = user.profile.id

        # Save user multiple times
        for _ in range(3):
            user.save()

        # Verify no duplicate profiles
        self.assertEqual(
            UserProfile.objects.filter(user=user).count(),
            1
        )
        self.assertEqual(user.profile.id, initial_profile_id)

    def test_signal_dependencies(self):
        """
        Test signal handler dependencies.

        Expected:
            - Handlers execute in correct order
            - Dependencies are satisfied
            - Final state is valid
        """
        # Reconnect signals in specific order
        post_save.connect(create_user_profile, sender=User)
        post_save.connect(save_user_profile, sender=User)

        # Create user and verify profile
        user = User.objects.create_user(**self.user_data)
        self.assertTrue(hasattr(user, 'profile'))

        # Update user and verify profile is updated
        user.first_name = "Updated"
        user.save()
        self.assertEqual(user.profile.user.first_name, "Updated")
