"""
Test cases for authentication serializers.

This module tests:
1. Input validation
2. Field transformations
3. Nested serialization
4. Custom field handling
5. Error cases
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from unittest.mock import patch

from authentication.models import UserProfile, Role
from authentication.v1.serializers import (
    UserSerializer,
    UserProfileSerializer,
    RegisterSerializer,
    LoginSerializer,
    GuestTokenSerializer,
    RoleSerializer,
    TokenSerializer
)

User = get_user_model()

class UserSerializerTestCase(TestCase):
    """Test suite for UserSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.serializer = UserSerializer(instance=self.user)

    def test_contains_expected_fields(self):
        """Test serializer contains all expected fields."""
        data = self.serializer.data
        expected_fields = {
            'id', 'username', 'email', 'first_name', 
            'last_name', 'is_active', 'date_joined'
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_password_write_only(self):
        """Test password field is write-only."""
        data = self.serializer.data
        self.assertNotIn('password', data)

    def test_username_validation(self):
        """Test username validation rules."""
        invalid_usernames = [
            'user@name',  # No special characters
            'ab',         # Too short
            'a' * 151,    # Too long
            '',          # Empty
            None         # None
        ]
        serializer = UserSerializer()
        for username in invalid_usernames:
            with self.assertRaises(ValidationError):
                serializer.validate_username(username)

    def test_email_validation(self):
        """Test email validation rules."""
        invalid_emails = [
            'invalid_email',
            '@example.com',
            'user@',
            'user@.com',
            ''
        ]
        serializer = UserSerializer()
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                serializer.validate_email(email)

class UserProfileSerializerTestCase(TestCase):
    """Test suite for UserProfileSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.profile_data = {
            'user': self.user,
            'bio': 'Test bio',
            'location': 'Test location',
            'preferences': {'theme': 'dark'}
        }
        self.profile = UserProfile.objects.create(**self.profile_data)
        self.serializer = UserProfileSerializer(instance=self.profile)

    def test_nested_user_serialization(self):
        """Test nested user data serialization."""
        data = self.serializer.data
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_preferences_validation(self):
        """Test preferences field validation."""
        invalid_preferences = [
            'not_a_dict',
            ['list_not_allowed'],
            {'invalid_key': {'nested': 'not_allowed'}},
            {'theme': None}
        ]
        serializer = UserProfileSerializer()
        for prefs in invalid_preferences:
            with self.assertRaises(ValidationError):
                serializer.validate_preferences(prefs)

    def test_read_only_fields(self):
        """Test read-only fields cannot be modified."""
        data = {
            'user': {'id': 999},
            'date_joined': '2024-01-01T00:00:00Z'
        }
        serializer = UserProfileSerializer(self.profile, data=data, partial=True)
        serializer.is_valid()
        updated_profile = serializer.save()
        self.assertEqual(updated_profile.user.id, self.user.id)

class RegisterSerializerTestCase(TestCase):
    """Test suite for RegisterSerializer."""

    def setUp(self):
        """Set up test data."""
        self.valid_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPass123!',
            'confirm_password': 'NewPass123!'
        }

    def test_passwords_match(self):
        """Test password confirmation validation."""
        data = self.valid_data.copy()
        data['confirm_password'] = 'DifferentPass123!'
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('confirm_password', serializer.errors)

    def test_password_complexity(self):
        """Test password complexity requirements."""
        invalid_passwords = [
            'short',           # Too short
            'onlylowercase',   # No uppercase
            'ONLYUPPERCASE',   # No lowercase
            'NoNumbers',       # No numbers
            'NoSpecial123'     # No special characters
        ]
        for password in invalid_passwords:
            data = self.valid_data.copy()
            data['password'] = password
            data['confirm_password'] = password
            serializer = RegisterSerializer(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn('password', serializer.errors)

    def test_unique_email(self):
        """Test email uniqueness validation."""
        User.objects.create_user(
            username='existing',
            email=self.valid_data['email'],
            password='TestPass123!'
        )
        serializer = RegisterSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

class LoginSerializerTestCase(TestCase):
    """Test suite for LoginSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.valid_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }

    def test_valid_credentials(self):
        """Test valid login credentials."""
        serializer = LoginSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_credentials(self):
        """Test invalid login credentials."""
        invalid_cases = [
            {'username': 'testuser', 'password': 'WrongPass123!'},
            {'username': 'wronguser', 'password': 'TestPass123!'},
            {'username': '', 'password': 'TestPass123!'},
            {'username': 'testuser', 'password': ''}
        ]
        for case in invalid_cases:
            serializer = LoginSerializer(data=case)
            self.assertFalse(serializer.is_valid())

    @patch('authentication.v1.serializers.authenticate')
    def test_inactive_user(self, mock_authenticate):
        """Test login attempt with inactive user."""
        self.user.is_active = False
        self.user.save()
        mock_authenticate.return_value = self.user
        
        serializer = LoginSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

class TokenSerializerTestCase(TestCase):
    """Test suite for TokenSerializer."""

    def setUp(self):
        """Set up test data."""
        self.token_data = {
            'access': 'test_access_token',
            'refresh': 'test_refresh_token'
        }

    def test_token_serialization(self):
        """Test token serialization."""
        serializer = TokenSerializer(data=self.token_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.data['access'], self.token_data['access'])
        self.assertEqual(serializer.data['refresh'], self.token_data['refresh'])

    def test_token_validation(self):
        """Test token validation."""
        invalid_tokens = [
            {'access': '', 'refresh': 'test_refresh_token'},
            {'access': 'test_access_token', 'refresh': ''},
            {'access': None, 'refresh': 'test_refresh_token'},
            {'refresh': 'test_refresh_token'}  # Missing access
        ]
        for token in invalid_tokens:
            serializer = TokenSerializer(data=token)
            self.assertFalse(serializer.is_valid())

class RoleSerializerTestCase(TestCase):
    """Test suite for RoleSerializer."""

    def setUp(self):
        """Set up test data."""
        self.role_data = {
            'name': 'test_role',
            'description': 'Test role description'
        }
        self.role = Role.objects.create(**self.role_data)
        self.serializer = RoleSerializer(instance=self.role)

    def test_role_serialization(self):
        """Test role serialization."""
        data = self.serializer.data
        self.assertEqual(data['name'], self.role_data['name'])
        self.assertEqual(data['description'], self.role_data['description'])

    def test_role_validation(self):
        """Test role validation."""
        invalid_roles = [
            {'name': '', 'description': 'Test'},
            {'name': 'a' * 151, 'description': 'Too long'},
            {'name': 'test_role', 'description': ''}  # Duplicate name
        ]
        for role_data in invalid_roles:
            serializer = RoleSerializer(data=role_data)
            self.assertFalse(serializer.is_valid())

    def test_role_update(self):
        """Test role update serialization."""
        update_data = {
            'name': 'updated_role',
            'description': 'Updated description'
        }
        serializer = RoleSerializer(self.role, data=update_data)
        self.assertTrue(serializer.is_valid())
        updated_role = serializer.save()
        self.assertEqual(updated_role.name, update_data['name'])
        self.assertEqual(updated_role.description, update_data['description']) 