"""
Test cases for custom middlewares.

This module tests:
1. Authentication middleware functionality
2. User location middleware functionality
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.conf import settings
from unittest.mock import Mock, patch
from coupon_core.custom_middlewares.authentication_middleware import AuthenticationMiddleware
from coupon_core.custom_middlewares.userlocation_middleware import UserLocationMiddleware

User = get_user_model()

class AuthenticationMiddlewareTestCase(TestCase):
    """Test suite for authentication middleware."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.middleware = AuthenticationMiddleware(get_response=Mock())
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_token_authentication(self):
        """Test token-based authentication."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer valid_token'
        
        with patch('authentication.v1.utils.token_manager.TokenManager.verify_token') as mock_verify:
            mock_verify.return_value = {'user_id': self.user.id}
            self.middleware(request)
            self.assertEqual(request.user, self.user)

    def test_invalid_token(self):
        """Test authentication with invalid token."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer invalid_token'
        
        with patch('authentication.v1.utils.token_manager.TokenManager.verify_token') as mock_verify:
            mock_verify.return_value = None
            self.middleware(request)
            self.assertTrue(request.user.is_anonymous)

    def test_missing_token(self):
        """Test request without authentication token."""
        request = self.factory.get('/')
        self.middleware(request)
        self.assertTrue(request.user.is_anonymous)

    def test_malformed_token(self):
        """Test authentication with malformed token."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'InvalidFormat token'
        self.middleware(request)
        self.assertTrue(request.user.is_anonymous)

    def test_expired_token(self):
        """Test authentication with expired token."""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION'] = 'Bearer expired_token'
        
        with patch('authentication.v1.utils.token_manager.TokenManager.verify_token') as mock_verify:
            mock_verify.side_effect = Exception('Token expired')
            self.middleware(request)
            self.assertTrue(request.user.is_anonymous)

class UserLocationMiddlewareTestCase(TestCase):
    """Test suite for user location middleware."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.middleware = UserLocationMiddleware(get_response=Mock())
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_location_headers(self):
        """Test processing of location headers."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1'
        request.user = self.user
        
        with patch('geodiscounts.utils.location.get_location_from_ip') as mock_location:
            mock_location.return_value = {
                'city': 'Test City',
                'country': 'Test Country',
                'latitude': 0.0,
                'longitude': 0.0
            }
            self.middleware(request)
            self.assertTrue(hasattr(request, 'user_location'))
            self.assertEqual(request.user_location['city'], 'Test City')

    def test_missing_location_headers(self):
        """Test behavior when location headers are missing."""
        request = self.factory.get('/')
        request.user = self.user
        self.middleware(request)
        self.assertTrue(hasattr(request, 'user_location'))
        self.assertIsNone(request.user_location)

    def test_invalid_ip_address(self):
        """Test handling of invalid IP addresses."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = 'invalid_ip'
        request.user = self.user
        
        with patch('geodiscounts.utils.location.get_location_from_ip') as mock_location:
            mock_location.return_value = None
            self.middleware(request)
            self.assertTrue(hasattr(request, 'user_location'))
            self.assertIsNone(request.user_location)

    def test_multiple_ip_addresses(self):
        """Test handling of multiple forwarded IP addresses."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1, 10.0.0.1'
        request.user = self.user
        
        with patch('geodiscounts.utils.location.get_location_from_ip') as mock_location:
            mock_location.return_value = {
                'city': 'Test City',
                'country': 'Test Country',
                'latitude': 0.0,
                'longitude': 0.0
            }
            self.middleware(request)
            self.assertTrue(hasattr(request, 'user_location'))
            self.assertEqual(request.user_location['city'], 'Test City')

    def test_location_caching(self):
        """Test caching of location data."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '192.168.1.1'
        request.user = self.user
        
        with patch('geodiscounts.utils.location.get_location_from_ip') as mock_location:
            mock_location.return_value = {
                'city': 'Test City',
                'country': 'Test Country',
                'latitude': 0.0,
                'longitude': 0.0
            }
            # First request should cache the location
            self.middleware(request)
            initial_location = request.user_location
            
            # Second request should use cached location
            mock_location.reset_mock()
            self.middleware(request)
            mock_location.assert_not_called()
            self.assertEqual(request.user_location, initial_location) 