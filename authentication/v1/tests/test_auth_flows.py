"""
Test cases for authentication flows.

This module tests:
1. Password reset flow
2. Email verification
3. Token refresh flow
4. Session management
5. Rate limiting
"""

from django.test import TestCase
from django.core import mail
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
import jwt
from datetime import timedelta

from authentication.models import UserProfile
from authentication.v1.utils.token_manager import TokenManager

User = get_user_model()

class PasswordResetFlowTestCase(APITestCase):
    """Test suite for password reset flow."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPass123!'
        )
        self.token_manager = TokenManager()

    def test_request_password_reset(self):
        """Test password reset request."""
        url = reverse('v1:password-reset-request')
        response = self.client.post(url, {'email': 'test@example.com'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset your password', mail.outbox[0].subject.lower())

    def test_invalid_email_reset_request(self):
        """Test password reset request with invalid email."""
        url = reverse('v1:password-reset-request')
        response = self.client.post(url, {'email': 'nonexistent@example.com'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Don't reveal user existence
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_password_with_token(self):
        """Test password reset with valid token."""
        # Generate reset token
        token = self.token_manager.create_password_reset_token(self.user)
        url = reverse('v1:password-reset-confirm')
        
        new_password = 'NewPass123!'
        response = self.client.post(url, {
            'token': token,
            'password': new_password,
            'confirm_password': new_password
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_reset_password_invalid_token(self):
        """Test password reset with invalid token."""
        url = reverse('v1:password-reset-confirm')
        response = self.client.post(url, {
            'token': 'invalid_token',
            'password': 'NewPass123!',
            'confirm_password': 'NewPass123!'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_rate_limiting(self):
        """Test rate limiting on password reset requests."""
        url = reverse('v1:password-reset-request')
        
        # Make multiple requests
        for _ in range(5):
            response = self.client.post(url, {'email': 'test@example.com'})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Next request should be rate limited
        response = self.client.post(url, {'email': 'test@example.com'})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

class EmailVerificationFlowTestCase(APITestCase):
    """Test suite for email verification flow."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=False
        )
        self.token_manager = TokenManager()

    def test_send_verification_email(self):
        """Test sending verification email."""
        url = reverse('v1:send-verification-email')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verify your email', mail.outbox[0].subject.lower())

    def test_verify_email(self):
        """Test email verification with token."""
        token = self.token_manager.create_email_verification_token(self.user)
        url = reverse('v1:verify-email')
        
        response = self.client.post(url, {'token': token})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_verify_email_invalid_token(self):
        """Test email verification with invalid token."""
        url = reverse('v1:verify-email')
        response = self.client.post(url, {'token': 'invalid_token'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_verify_email_expired_token(self):
        """Test email verification with expired token."""
        with patch('authentication.v1.utils.token_manager.timezone.now') as mock_now:
            # Create token
            token = self.token_manager.create_email_verification_token(self.user)
            
            # Set time to after token expiration
            mock_now.return_value = timezone.now() + timedelta(days=8)
            
            url = reverse('v1:verify-email')
            response = self.client.post(url, {'token': token})
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('expired', str(response.data).lower())

class TokenRefreshFlowTestCase(APITestCase):
    """Test suite for token refresh flow."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.token_manager = TokenManager()
        self.access_token = self.token_manager.create_access_token(self.user)
        self.refresh_token = self.token_manager.create_refresh_token(self.user)

    def test_refresh_token(self):
        """Test refreshing access token."""
        url = reverse('v1:token-refresh')
        response = self.client.post(url, {'refresh': self.refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotEqual(response.data['access'], self.access_token)

    def test_refresh_token_expired(self):
        """Test refreshing with expired token."""
        with patch('authentication.v1.utils.token_manager.timezone.now') as mock_now:
            # Set time to after token expiration
            mock_now.return_value = timezone.now() + timedelta(days=8)
            
            url = reverse('v1:token-refresh')
            response = self.client.post(url, {'refresh': self.refresh_token})
            
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn('expired', str(response.data).lower())

    def test_refresh_token_blacklisted(self):
        """Test refreshing with blacklisted token."""
        # Blacklist the refresh token
        self.token_manager.blacklist_token(self.refresh_token)
        
        url = reverse('v1:token-refresh')
        response = self.client.post(url, {'refresh': self.refresh_token})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('blacklisted', str(response.data).lower())

class SessionManagementTestCase(APITestCase):
    """Test suite for session management."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.token_manager = TokenManager()

    def test_login_creates_session(self):
        """Test session creation on login."""
        url = reverse('v1:login')
        response = self.client.post(url, {
            'username': 'testuser',
            'password': 'TestPass123!'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_logout_all_sessions(self):
        """Test logging out all sessions."""
        # Create multiple sessions
        tokens = []
        for _ in range(3):
            tokens.append({
                'access': self.token_manager.create_access_token(self.user),
                'refresh': self.token_manager.create_refresh_token(self.user)
            })

        # Logout all sessions
        self.client.force_authenticate(user=self.user)
        url = reverse('v1:logout-all')
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all refresh tokens are blacklisted
        url = reverse('v1:token-refresh')
        for token in tokens:
            response = self.client.post(url, {'refresh': token['refresh']})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_inactivity_timeout(self):
        """Test session timeout after inactivity."""
        with patch('authentication.v1.utils.token_manager.timezone.now') as mock_now:
            # Create token
            access_token = self.token_manager.create_access_token(self.user)
            
            # Set time to after inactivity timeout
            mock_now.return_value = timezone.now() + timedelta(minutes=30)
            
            # Try to use token
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
            url = reverse('v1:userprofile')
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertIn('expired', str(response.data).lower()) 