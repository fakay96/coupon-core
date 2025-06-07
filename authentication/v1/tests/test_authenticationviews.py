import unittest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from authentication.models import CustomUser


class AuthenticationViewsTestCase(TestCase):
    """Test suite for authentication views."""

    def setUp(self):
        self.client = APIClient()
        # Create a verified user
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
        )
        # Ensure the profile is activated in the DB
        self.user.activated_profile = True
        self.user.save()

   

    def test_register_invalid_payload(self):
        url = reverse('auth:register')
        # Missing email and password2 fields
        data = {'username': 'u', 'password': 'p'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)
        self.assertIn('email', response.data['errors'])

    def test_register_duplicate(self):
        url = reverse('auth:register')
        # Seed duplicate user
        CustomUser.objects.create_user(
            username='dupuser',
            email='dup@example.com',
            password='DupPass123!',
        )
        data = {
            'username': 'dupuser',
            'email': 'dup@example.com',
            'password': 'DupPass123!',
            'password2': 'DupPass123!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Expect unique-field validation errors
        self.assertIn('errors', response.data)
        self.assertIn('username', response.data['errors'])
        self.assertIn('email', response.data['errors'])

    def test_register_password_mismatch(self):
        """Registration should fail when passwords do not match."""
        url = reverse('auth:register')
        data = {
            'username': 'user2',
            'email': 'user2@example.com',
            'password': 'StrongPass1!',
            'password2': 'WrongPass1!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_login_success(self):
        url = reverse('auth:login')
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return both tokens
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_not_verified(self):
        # Create unverified user
        unverified = CustomUser.objects.create_user(
            username='u2',
            email='u2@example.com',
            password='P@ssw0rd',
        )
        # Ensure not activated
        unverified.activated_profile = False
        unverified.save()

        url = reverse('auth:login')
        data = {'email': 'u2@example.com', 'password': 'P@ssw0rd'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)

    def test_login_invalid(self):
        url = reverse('auth:login')
        data = {'email': 'test@example.com', 'password': 'WrongPass!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_login_missing_password(self):
        """Login should fail if the password is missing."""
        url = reverse('auth:login')
        data = {'email': 'test@example.com'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_userinfo_success(self):
        # Authenticate user for fetching user info
        self.client.force_authenticate(user=self.user)
        url = reverse('auth:user-info')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in (
            'id', 'username', 'email', 'role',
            'is_staff', 'is_active', 'date_joined', 'last_login'
        ):
            self.assertIn(field, response.data)

    def test_userinfo_guest_forbidden(self):
        guest = CustomUser.objects.create_user(
            username='guest',
            email='g@example.com',
            password='p',
        )
        guest.is_guest = True
        guest.save()
        self.client.force_authenticate(user=guest)
        url = reverse('auth:user-info')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)

    @unittest.skip("Password reset tests skipped until implementation stabilizes")
    def test_password_reset_success(self):
        pass

    @unittest.skip("Password reset tests skipped until implementation stabilizes")
    def test_password_reset_invalid(self):
        pass

    @unittest.skip("Password reset tests skipped until implementation stabilizes")
    def test_password_reset_store_error(self):
        pass