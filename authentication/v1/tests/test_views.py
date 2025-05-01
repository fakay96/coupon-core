"""
Test cases for authentication views.

This module tests:
1. View responses
2. Authentication flows
3. Error handling
4. Edge cases
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from authentication.models import UserProfile, PasswordResetRequest
import json
import tempfile
from PIL import Image
import io
from django.utils import timezone

User = get_user_model()

class AuthenticationViewsTestCase(TestCase):
    """Test suite for authentication views."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=self.user)

    def test_register_view(self):
        """Test user registration."""
        url = reverse('auth:register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPass123!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_view(self):
        """Test user login."""
        url = reverse('auth:login')
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_logout_view(self):
        """Test user logout."""
        url = reverse('auth:logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_request(self):
        """Test password reset request."""
        url = reverse('auth:password-reset-request')
        data = {'email': 'test@example.com'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetRequest.objects.filter(user=self.user).exists())

    def test_password_reset_confirm(self):
        """Test password reset confirmation."""
        # Create password reset request
        reset_request = PasswordResetRequest.objects.create(user=self.user)
        url = reverse('auth:password-reset-confirm', args=[reset_request.token])
        data = {'password': 'NewPass123!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123!'))

    def test_guest_token_view(self):
        """Test guest token generation."""
        url = reverse('auth:guest-token')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user_id', response.data)

    def test_invalid_login(self):
        """Test login with invalid credentials."""
        url = reverse('auth:login')
        data = {
            'email': 'test@example.com',
            'password': 'WrongPass123!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_registration(self):
        """Test registration with existing email."""
        url = reverse('auth:register')
        data = {
            'username': 'anotheruser',
            'email': 'test@example.com',
            'password': 'NewPass123!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_password_reset(self):
        """Test password reset with invalid token."""
        url = reverse('auth:password-reset-confirm', args=['invalid-token'])
        data = {'password': 'NewPass123!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_token_limits(self):
        """Test guest token usage limits."""
        url = reverse('auth:guest-token')
        # Create multiple guest tokens
        for _ in range(5):
            response = self.client.post(url)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify only one guest user exists
        self.assertEqual(User.objects.filter(is_guest=True).count(), 1)

    def test_password_reset_request_rate_limit(self):
        """Test rate limiting for password reset requests."""
        url = reverse('auth:password-reset-request')
        data = {'email': 'test@example.com'}
        
        # Make multiple requests in quick succession
        for _ in range(5):
            response = self.client.post(url, data, format='json')
        
        # Sixth request should be rate limited
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_password_reset_token_expiry(self):
        """Test password reset token expiry."""
        # Create password reset request
        reset_request = PasswordResetRequest.objects.create(user=self.user)
        
        # Simulate token expiry
        reset_request.created_at = timezone.now() - timezone.timedelta(hours=25)
        reset_request.save()
        
        url = reverse('auth:password-reset-confirm', args=[reset_request.token])
        data = {'password': 'NewPass123!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_token_expiry(self):
        """Test guest token expiry."""
        url = reverse('auth:guest-token')
        response = self.client.post(url)
        token = response.data['token']
        
        # Simulate token expiry
        guest_user = User.objects.get(id=response.data['user_id'])
        guest_user.date_joined = timezone.now() - timezone.timedelta(days=2)
        guest_user.save()
        
        # Try to use expired token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('auth:profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class UserProfileViewTests(APITestCase):
    """Test cases for user profile views."""

    databases = {'default', 'authentication_shard'}  # Specify required databases

    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.client.force_authenticate(user=self.user)
        self.profile_url = reverse('auth:profile')

    def test_get_profile(self):
        """Test retrieving user profile."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], self.user.email)
        self.assertEqual(response.data['user']['username'], self.user.username)

    def test_update_profile(self):
        """Test updating user profile."""
        data = {
            'bio': 'Test bio',
            'location': 'Test City',
            'preferences': {'theme': 'dark', 'notifications': True}
        }
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bio'], data['bio'])
        self.assertEqual(response.data['location'], data['location'])
        self.assertEqual(response.data['preferences'], data['preferences'])

    def test_update_profile_invalid_data(self):
        """Test updating profile with invalid data."""
        data = {
            'preferences': 'invalid'  # Should be a dict
        }
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def create_test_image(self):
        """Create a test image file."""
        file = io.BytesIO()
        image = Image.new('RGB', (100, 100), 'white')
        image.save(file, 'PNG')
        file.seek(0)
        return SimpleUploadedFile('test.png', file.getvalue(), content_type='image/png')

    def test_update_profile_image(self):
        """Test updating profile image."""
        image = self.create_test_image()
        data = {'profile_image': image}
        response = self.client.patch(self.profile_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('profile_image' in response.data)
        self.assertTrue(response.data['profile_image'].endswith('.png'))

    def test_update_profile_invalid_image(self):
        """Test updating profile with invalid image."""
        invalid_file = SimpleUploadedFile('test.txt', b'invalid image content', content_type='text/plain')
        data = {'profile_image': invalid_file}
        response = self.client.patch(self.profile_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_profile_image(self):
        """Test deleting profile image."""
        # First upload an image
        image = self.create_test_image()
        self.client.patch(self.profile_url, {'profile_image': image}, format='multipart')
        
        # Then delete it
        data = {'profile_image': None}
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['profile_image'])

    def test_unauthenticated_access(self):
        """Test accessing profile without authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_preferences(self):
        """Test updating user preferences."""
        preferences = {
            'theme': 'light',
            'notifications': {
                'email': True,
                'push': False
            },
            'language': 'en'
        }
        data = {'preferences': preferences}
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preferences'], preferences)

    def test_partial_preference_update(self):
        """Test partial update of preferences."""
        # Set initial preferences
        initial_prefs = {'theme': 'dark', 'notifications': True}
        self.profile.preferences = initial_prefs
        self.profile.save()
        
        # Update only one preference
        update_data = {'preferences': {'theme': 'light'}}
        response = self.client.patch(self.profile_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['preferences']['theme'], 'light')
        self.assertEqual(response.data['preferences']['notifications'], True)

    def test_invalid_preference_format(self):
        """Test updating preferences with invalid format."""
        invalid_prefs = ['invalid', 'format']
        data = {'preferences': invalid_prefs}
        response = self.client.patch(self.profile_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_image_size_limit(self):
        """Test profile image size limit."""
        # Create a large image
        file = io.BytesIO()
        image = Image.new('RGB', (2000, 2000), 'white')
        image.save(file, 'PNG')
        file.seek(0)
        large_image = SimpleUploadedFile('large.png', file.getvalue(), content_type='image/png')
        
        data = {'profile_image': large_image}
        response = self.client.patch(self.profile_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_preferences_validation(self):
        """Test profile preferences validation."""
        invalid_preferences = [
            {'theme': 123},  # Invalid theme type
            {'notifications': 'invalid'},  # Invalid notification type
            {'language': ['en']}  # Invalid language type
        ]
        
        for prefs in invalid_preferences:
            data = {'preferences': prefs}
            response = self.client.patch(self.profile_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_location_validation(self):
        """Test profile location validation."""
        invalid_locations = [
            {'lat': 91, 'lng': 0},  # Invalid latitude
            {'lat': 0, 'lng': 181},  # Invalid longitude
            {'lat': 'invalid', 'lng': 0},  # Invalid type
            {'lat': 0}  # Missing longitude
        ]
        
        for loc in invalid_locations:
            data = {'location': loc}
            response = self.client.patch(self.profile_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class UserProfileBulkOperationsTestCase(APITestCase):
    """Test suite for bulk profile operations."""

    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client.force_authenticate(user=self.admin_user)
        self.bulk_url = reverse('auth:bulk-profiles')
        
        # Create test users
        self.users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)

    def test_bulk_retrieve_profiles(self):
        """Test retrieving multiple profiles."""
        user_ids = [user.id for user in self.users]
        response = self.client.post(self.bulk_url, {'user_ids': user_ids}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(user_ids))

    def test_bulk_update_profiles(self):
        """Test updating multiple profiles."""
        updates = [
            {
                'user_id': self.users[0].id,
                'bio': 'New bio 1',
                'location': 'Location 1'
            },
            {
                'user_id': self.users[1].id,
                'bio': 'New bio 2',
                'location': 'Location 2'
            }
        ]
        response = self.client.patch(self.bulk_url, {'updates': updates}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify updates
        for update in updates:
            profile = UserProfile.objects.get(user_id=update['user_id'])
            self.assertEqual(profile.bio, update['bio'])
            self.assertEqual(profile.location, update['location'])

    def test_bulk_delete_profiles(self):
        """Test deleting multiple profiles."""
        user_ids = [self.users[0].id, self.users[1].id]
        response = self.client.delete(self.bulk_url, {'user_ids': user_ids}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deletions
        for user_id in user_ids:
            with self.assertRaises(User.DoesNotExist):
                User.objects.get(id=user_id)

    def test_bulk_operations_non_admin(self):
        """Test bulk operations with non-admin user."""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='regular123'
        )
        self.client.force_authenticate(user=regular_user)
        
        response = self.client.post(self.bulk_url, {'user_ids': []}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_update_validation(self):
        """Test validation in bulk updates."""
        invalid_updates = [
            {
                'user_id': self.users[0].id,
                'preferences': 'invalid'  # Invalid preferences format
            },
            {
                'user_id': self.users[1].id,
                'location': {'lat': 91, 'lng': 0}  # Invalid location
            }
        ]
        response = self.client.patch(self.bulk_url, {'updates': invalid_updates}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_operation_partial_success(self):
        """Test partial success in bulk operations."""
        updates = [
            {
                'user_id': self.users[0].id,
                'bio': 'Valid bio'
            },
            {
                'user_id': 999999,  # Non-existent user
                'bio': 'Invalid bio'
            }
        ]
        response = self.client.patch(self.bulk_url, {'updates': updates}, format='json')
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertTrue(any(r['status'] == 'error' for r in response.data))
        self.assertTrue(any(r['status'] == 'success' for r in response.data)) 