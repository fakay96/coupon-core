"""
Test cases for authentication views.

This module tests:
1. User profile views
2. Profile update operations
3. Profile preferences
4. Profile image handling
"""

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from authentication.models import UserProfile
import json
import tempfile
from PIL import Image
import io

User = get_user_model()

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