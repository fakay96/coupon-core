import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
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
from unittest.mock import patch, MagicMock
from django.contrib.gis.geos import Point

from authentication.models import UserProfile, Role
from authentication.v1.serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    GuestTokenSerializer,
    PasswordResetSerializer
)

User = get_user_model()

class LoginSerializerTestCase(TestCase):
    """Test suite for LoginSerializer."""
    
    databases = {'default', 'authentication_shard'}

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def setUp(self, mock_reset_email, mock_verification_email):
        """Set up test data."""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.serializer = LoginSerializer()

    def test_contains_expected_fields(self):
        """Test serializer contains all expected fields."""
        data = self.serializer.get_fields()
        expected_fields = {'email', 'password'}
        self.assertEqual(set(data.keys()), expected_fields)

    def test_password_write_only(self):
        """Test password field is write-only."""
        data = self.serializer.get_fields()
        self.assertTrue(data['password'].write_only)

    def test_email_validation(self):
        """Test email validation rules."""
        invalid_emails = [
            'invalid_email',
            '@example.com',
            'user@',
            'user@.com',
            ''
        ]
        for email in invalid_emails:
            serializer = LoginSerializer(data={'email': email, 'password': 'TestPass123!'})
            self.assertFalse(serializer.is_valid())
            self.assertIn('email', serializer.errors)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_valid_credentials(self, mock_reset_email, mock_verification_email):
        """Test valid login credentials."""
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], self.user)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_invalid_credentials(self, mock_reset_email, mock_verification_email):
        invalid_cases = [
            {'email': 'test@example.com', 'password': 'WrongPass123!'},
            {'email': 'wrong@example.com', 'password': 'TestPass123!'},
            {'email': '', 'password': 'TestPass123!'},
            {'email': 'test@example.com', 'password': ''}
        ]
        for case in invalid_cases:
            serializer = LoginSerializer(data=case)
            self.assertFalse(serializer.is_valid())

            if case.get('email') and case.get('password'):
                self.assertIn('non_field_errors', serializer.errors)
            else:
                self.assertTrue(any(field in serializer.errors for field in ['email', 'password']))


    def test_password_validation_rules(self):
        """Test password validation rules."""
        invalid_passwords = [
            'short',  # Too short
            'no_uppercase123!',  # No uppercase
            'NO_LOWERCASE123!',  # No lowercase
            'NoSpecialChar123',  # No special char
            'NoNumbers!!',  # No numbers
            ''  # Empty
        ]
        for password in invalid_passwords:
            with self.assertRaises(ValidationError):
                self.serializer.validate_password(password)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_email_case_insensitivity(self, mock_reset_email, mock_verification_email):
        """Test email case insensitivity."""
        data = {
            'email': 'TEST@example.com',
            'password': 'TestPass123!'
        }
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'].lower(), 'test@example.com')

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_guest_user_login(self, mock_reset_email, mock_verification_email):
        """Test guest users cannot log in."""
        # Create a guest user
        guest_user = User.objects.create_user(
            username='guest',
            email='guest@example.com',
            password='TestPass123!',
            is_guest=True
        )
        
        data = {
            'email': 'guest@example.com',
            'password': 'TestPass123!'
        }
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

class UserProfileSerializerTestCase(TestCase):
    """Test suite for UserProfileSerializer."""
    
    databases = {'default', 'authentication_shard'}

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def setUp(self, mock_reset_email, mock_verification_email):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        # The UserProfile will be created by the signal
        self.profile = self.user.profile
        self.profile.preferences = {'theme': 'dark'}
        self.profile.location = Point(0.0, 0.0)
        self.profile.save()
        self.serializer = UserProfileSerializer(instance=self.profile)

    def test_contains_expected_fields(self):
        """Test serializer contains all expected fields."""
        data = self.serializer.data
        expected_fields = {
            'first_name', 'last_name', 'phone_number',
            'preferences', 'profile_image'
        }
        self.assertEqual(set(data.keys()), expected_fields)

    def test_preferences_validation(self):
        """Test preferences field validation."""
        invalid_preferences = [
            'not_a_dict',
            ['list_not_allowed'],
            {'invalid_key': {'nested': 'not_allowed'}},
            {'theme': None}
        ]
        for prefs in invalid_preferences:
            serializer = UserProfileSerializer(data={'preferences': prefs})
            self.assertFalse(serializer.is_valid())
            self.assertIn('preferences', serializer.errors)

    def test_location_validation(self):
        """Test location field validation."""
        invalid_locations = [
            [0.0],  # Missing latitude
            [0.0, 0.0, 0.0],  # Extra coordinate
            ['invalid', 'invalid'],  # Non-numeric values
            [200.0, 100.0]  # Invalid coordinates
        ]
        for loc in invalid_locations:
            serializer = UserProfileSerializer(data={'location': loc})
            self.assertFalse(serializer.is_valid())
            self.assertIn('location', serializer.errors)

    def test_preferences_nested_validation(self):
        """Test nested preferences validation."""
        invalid_nested_prefs = [
            {
                'notifications': {
                    'email': 'invalid',  # Should be boolean
                    'push': 123  # Should be boolean
                }
            },
            {
                'theme': {
                    'primary': '#invalid',  # Invalid color
                    'secondary': 123  # Invalid type
                }
            }
        ]
        for prefs in invalid_nested_prefs:
            serializer = UserProfileSerializer(data={'preferences': prefs})
            self.assertFalse(serializer.is_valid())
            self.assertIn('preferences', serializer.errors)

    def test_location_coordinate_validation(self):
        """Test location coordinate validation."""
        invalid_coordinates = [
            {'lat': 91, 'lng': 0},  # Invalid latitude
            {'lat': -91, 'lng': 0},  # Invalid latitude
            {'lat': 0, 'lng': 181},  # Invalid longitude
            {'lat': 0, 'lng': -181},  # Invalid longitude
            {'lat': 'invalid', 'lng': 0},  # Invalid type
            {'lat': 0, 'lng': 'invalid'}  # Invalid type
        ]
        for coords in invalid_coordinates:
            serializer = UserProfileSerializer(data={'location': [coords['lng'], coords['lat']]})
            self.assertFalse(serializer.is_valid())
            self.assertIn('location', serializer.errors)

class RegisterSerializerTestCase(TestCase):
    """Test suite for RegisterSerializer."""
    
    databases = {'default', 'authentication_shard'}

    def setUp(self):
        """Set up test data."""
        self.serializer = RegisterSerializer()
        self.valid_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password_confirmation': 'TestPass123!'
        }

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_password_hashing(self, mock_reset_email, mock_verification_email):
        """Test password is hashed during user creation."""
        serializer = RegisterSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertNotEqual(user.password, self.valid_data['password'])

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_unique_email(self, mock_reset_email, mock_verification_email):
        """Test email uniqueness validation."""
        User.objects.create_user(
            username='existing',
            email=self.valid_data['email'],
            password='TestPass123!'
        )
        serializer = RegisterSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_username_validation(self):
        """Test username validation rules."""
        invalid_usernames = [
            'invalid@username',  # Contains @
            'ab',  # Too short
            'a' * 31,  # Too long
            'user name',  # Contains space
            'user/name',  # Contains invalid char
        ]
        for username in invalid_usernames:
            data = self.valid_data.copy()
            data['username'] = username
            serializer = RegisterSerializer(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn('username', serializer.errors)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_password_confirmation(self, mock_reset_email, mock_verification_email):
        """Test password confirmation validation."""
        # Test matching passwords
        data = self.valid_data.copy()
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Test mismatched passwords
        data['password_confirmation'] = 'DifferentPass123!'
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_guest_user_limits(self, mock_reset_email, mock_verification_email):
        """Test guest user creation limits."""
        # Create maximum number of guest users
        for i in range(5):
            User.objects.create_user(
                username=f'guest{i}',
                email=f'guest{i}@example.com',
                password='TestPass123!',
                is_guest=True
            )

        # Try to create another guest user
        data = self.valid_data.copy()
        data['is_guest'] = True
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

class GuestTokenSerializerTestCase(TestCase):
    """Test suite for GuestTokenSerializer."""
    
    databases = {'default', 'authentication_shard'}

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def setUp(self, mock_reset_email, mock_verification_email):
        """Set up test data."""
        self.serializer = GuestTokenSerializer()
        self.valid_data = {
            'email': 'guest@example.com'
        }

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_guest_user_creation(self, mock_reset_email, mock_verification_email):
        """Test guest user creation."""
        serializer = GuestTokenSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        email = serializer.validated_data['email']
        user = serializer.get_abstract_user(email)
        self.assertTrue(user.is_guest)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_existing_user_retrieval(self, mock_reset_email, mock_verification_email):
        """Test retrieval of existing guest user."""
        User.objects.create_user(
            username='guest',
            email=self.valid_data['email'],
            password='TestPass123!',
            is_guest=True
        )
        serializer = GuestTokenSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        email = serializer.validated_data['email']
        user = serializer.get_abstract_user(email)
        self.assertTrue(user.is_guest)

    @patch('authentication.v1.tasks.verification_task.send_verification_email_task.delay')
    @patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
    def test_guest_user_limits(self, mock_reset_email, mock_verification_email):
        """Test guest user creation limits."""
        # Create maximum number of guest users
        for i in range(5):
            User.objects.create_user(
                username=f'guest{i}',
                email=f'guest{i}@example.com',
                password='TestPass123!',
                is_guest=True
            )

        # Try to create another guest user
        serializer = GuestTokenSerializer(data={'email': 'guest6@example.com'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)


@patch('authentication.v1.tasks.verification_task.send_password_reset_email_task.delay')
@patch('authentication.v1.serializers.PasswordResetRequest.objects.filter')
class PasswordResetSerializerTestCase(TestCase):
    databases = {'default', 'authentication_shard'}

    def setUp(self):
        self.email = 'test@example.com'
        with patch('authentication.v1.signals.send_password_reset_email'):
            self.user = User.objects.create_user(
                username='testuser',
                email=self.email,
                password='TestPass123!'
            )

    def test_valid_email(self, mock_filter, mock_send_task):
        mock_filter.return_value.exists.return_value = False
        serializer = PasswordResetSerializer(data={'email': self.email})
        self.assertTrue(serializer.is_valid())

    def test_password_reset_email_sent(self, mock_filter, mock_send_task):
        mock_filter.return_value.exists.return_value = False
        mock_send_task.return_value = MagicMock()

        serializer = PasswordResetSerializer(data={'email': self.email})
        self.assertTrue(serializer.is_valid())

        with patch('authentication.v1.serializers.PasswordResetRequest.objects.create') as mock_create:
            mock_create.return_value.token = 'mock-token'
            serializer.save()

        mock_send_task.assert_called_once()
        self.assertEqual(mock_send_task.call_args[0][0], self.email)

    
