"""
Test cases for authentication models.

This module tests:
1. CustomUser model functionality
2. UserProfile model functionality
3. Model methods and properties
4. Model constraints and validations
"""

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.test import TestCase

from authentication.models import CustomUser, UserProfile, Role


class CustomUserModelTestCase(TestCase):
    """Test suite for CustomUser model."""

    def setUp(self) -> None:
        """Set up test data."""
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User"
        }
        self.user = CustomUser.objects.create_user(**self.user_data)

    def test_create_user(self) -> None:
        """
        Test user creation with valid data.

        Validates:
            - User is created successfully
            - Default values are set correctly
            - Password is hashed
        """
        self.assertEqual(self.user.username, self.user_data["username"])
        self.assertEqual(self.user.email, self.user_data["email"])
        self.assertTrue(self.user.check_password(self.user_data["password"]))
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_guest)

    def test_create_superuser(self) -> None:
        """
        Test superuser creation.

        Validates:
            - Superuser is created with correct permissions
            - Cannot create superuser with is_staff=False
            - Cannot create superuser with is_superuser=False
        """
        superuser = CustomUser.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123"
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

        # Test creating superuser with is_staff=False
        with self.assertRaises(ValueError):
            CustomUser.objects.create_superuser(
                username="admin2",
                email="admin2@example.com",
                password="admin123",
                is_staff=False
            )

        # Test creating superuser with is_superuser=False
        with self.assertRaises(ValueError):
            CustomUser.objects.create_superuser(
                username="admin3",
                email="admin3@example.com",
                password="admin123",
                is_superuser=False
            )

    def test_user_str_representation(self) -> None:
        """Test the string representation of the user model."""
        self.assertEqual(str(self.user), self.user_data["username"])

    def test_user_email_unique(self) -> None:
        """Test that users cannot be created with duplicate emails."""
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                username="another",
                email=self.user_data["email"],  # Same email as existing user
                password="password123"
            )

    def test_user_username_unique(self) -> None:
        """Test that users cannot be created with duplicate usernames."""
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                username=self.user_data["username"],  # Same username as existing user
                email="another@example.com",
                password="password123"
            )

    def test_create_user_without_username(self) -> None:
        """Test that users cannot be created without a username."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                username="",
                email="test@example.com",
                password="password123"
            )

    def test_create_user_without_email(self) -> None:
        """Test that users cannot be created without an email."""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                username="testuser2",
                email="",
                password="password123"
            )


class UserProfileModelTestCase(TestCase):
    """Test suite for UserProfile model."""

    def setUp(self) -> None:
        """Set up test data."""
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        self.profile = UserProfile.objects.get(user=self.user)  # Created by signal

    def test_profile_creation(self) -> None:
        """
        Test profile creation and default values.

        Validates:
            - Profile is created with default values
            - Profile is linked to correct user
        """
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)
        self.assertIsNone(self.profile.preferences)
        self.assertIsNone(self.profile.location)

    def test_profile_update(self) -> None:
        """
        Test updating profile fields.

        Validates:
            - Can update preferences
            - Can update location
            - Updates are saved correctly
        """
        # Update preferences
        preferences = {"theme": "dark", "notifications": True}
        self.profile.preferences = preferences
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.preferences, preferences)

        # Update location
        location = Point(1.0, 2.0)
        self.profile.location = location
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.location, location)

    def test_profile_str_representation(self) -> None:
        """Test the string representation of the profile model."""
        expected = f"Profile of {self.user.username}"
        self.assertEqual(str(self.profile), expected)

    def test_profile_cascade_delete(self) -> None:
        """Test that profile is deleted when user is deleted."""
        profile_id = self.profile.id
        self.user.delete()
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)

    def test_profile_preferences_validation(self) -> None:
        """
        Test validation of preferences field.

        Validates:
            - Can save valid JSON
            - Cannot save invalid JSON
        """
        # Valid JSON
        valid_preferences = {
            "theme": "dark",
            "notifications": {
                "email": True,
                "push": False
            }
        }
        self.profile.preferences = valid_preferences
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.preferences, valid_preferences)

        # Invalid JSON (trying to save a function or complex object)
        with self.assertRaises(ValidationError):
            self.profile.preferences = lambda x: x
            self.profile.save()


class RoleModelTestCase(TestCase):
    """Test suite for Role model."""

    def setUp(self) -> None:
        """Set up test data."""
        self.role = Role.objects.create(
            name="test_role",
            description="Test role description"
        )

    def test_role_creation(self) -> None:
        """
        Test role creation with valid data.

        Validates:
            - Role is created with correct values
            - Timestamps are set
        """
        self.assertEqual(self.role.name, "test_role")
        self.assertEqual(self.role.description, "Test role description")
        self.assertIsNotNone(self.role.created_at)
        self.assertIsNotNone(self.role.updated_at)

    def test_role_str_representation(self) -> None:
        """Test the string representation of the role model."""
        self.assertEqual(str(self.role), "test_role")

    def test_role_name_unique(self) -> None:
        """Test that roles cannot be created with duplicate names."""
        with self.assertRaises(Exception):
            Role.objects.create(
                name="test_role",  # Same name as existing role
                description="Another description"
            )

    def test_role_name_min_length(self) -> None:
        """Test role name minimum length validation."""
        with self.assertRaises(ValidationError):
            role = Role(name="ab", description="Too short name")
            role.full_clean()

    def test_role_timestamps(self) -> None:
        """
        Test that timestamps are updated correctly.

        Validates:
            - created_at remains unchanged on update
            - updated_at changes on update
        """
        original_created_at = self.role.created_at
        original_updated_at = self.role.updated_at

        # Wait a moment to ensure timestamp will be different
        import time
        time.sleep(0.1)

        self.role.description = "Updated description"
        self.role.save()
        self.role.refresh_from_db()

        self.assertEqual(self.role.created_at, original_created_at)
        self.assertGreater(self.role.updated_at, original_updated_at) 