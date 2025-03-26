"""
Tests for custom middleware used in the Geodiscount API.

This module tests:
1. Rate limiting middleware
2. Request logging middleware
3. IP geolocation middleware
4. Cache control middleware
5. Error handling middleware
"""

from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from rest_framework import status
from geodiscounts.v1.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    IPGeolocationMiddleware,
    CacheControlMiddleware,
    ErrorHandlingMiddleware,
)
from django.core.cache import cache
import time
from django.core.exceptions import ObjectDoesNotExist
import json

User = get_user_model()

class BaseMiddlewareTest(TestCase):
    """Base class for middleware tests."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def get_response(self, request):
        """Mock get_response function."""
        return HttpResponse("Test response")


class RateLimitMiddlewareTest(BaseMiddlewareTest):
    """Tests for rate limiting middleware."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.middleware = RateLimitMiddleware(self.get_response)
        cache.clear()

    def test_rate_limit_exceeded(self):
        """Test rate limit being exceeded."""
        request = self.factory.get('/api/test/')
        request.user = self.user

        # Make requests up to the limit
        for _ in range(60):  # Assuming 60 requests per minute limit
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Next request should be rate limited
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)

    def test_rate_limit_reset(self):
        """Test rate limit reset after window expiry."""
        request = self.factory.get('/api/test/')
        request.user = self.user

        # Make some requests
        for _ in range(30):
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Wait for rate limit window to expire
        time.sleep(61)  # Wait just over a minute
        
        # Should be able to make requests again
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_different_endpoints(self):
        """Test rate limits for different endpoints."""
        request1 = self.factory.get('/api/endpoint1/')
        request2 = self.factory.get('/api/endpoint2/')
        request1.user = request2.user = self.user

        # Make requests to first endpoint
        for _ in range(60):
            response = self.middleware(request1)
            self.assertEqual(response.status_code, 200)

        # Should still be able to make requests to second endpoint
        response = self.middleware(request2)
        self.assertEqual(response.status_code, 200)


class RequestLoggingMiddlewareTest(BaseMiddlewareTest):
    """Tests for request logging middleware."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.middleware = RequestLoggingMiddleware(self.get_response)

    @patch('geodiscounts.v1.middleware.logger')
    def test_log_request(self, mock_logger):
        """Test request logging."""
        request = self.factory.get('/api/test/')
        request.user = self.user
        self.middleware(request)
        
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn('/api/test/', log_message)
        self.assertIn('testuser', log_message)

    @patch('geodiscounts.v1.middleware.logger')
    def test_log_slow_request(self, mock_logger):
        """Test logging of slow requests."""
        def slow_response(request):
            time.sleep(1)  # Simulate slow response
            return HttpResponse()

        middleware = RequestLoggingMiddleware(slow_response)
        request = self.factory.get('/api/test/')
        request.user = self.user
        middleware(request)
        
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]
        self.assertIn('Slow request', log_message)


class IPGeolocationMiddlewareTest(BaseMiddlewareTest):
    """Tests for IP geolocation middleware."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.middleware = IPGeolocationMiddleware(self.get_response)
        self.test_location = {
            'latitude': 37.751,
            'longitude': -97.822,
            'city': 'Test City',
            'country': 'Test Country'
        }

    @patch('geodiscounts.v1.utils.ip_geolocation.get_location_from_ip')
    def test_add_location_to_request(self, mock_get_location):
        """Test adding location data to request."""
        mock_get_location.return_value = self.test_location
        
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = '8.8.8.8'
        
        self.middleware(request)
        self.assertEqual(request.location, self.test_location)

    @patch('geodiscounts.v1.utils.ip_geolocation.get_location_from_ip')
    def test_handle_geolocation_error(self, mock_get_location):
        """Test handling geolocation errors."""
        mock_get_location.side_effect = ValueError("Geolocation failed")
        
        request = self.factory.get('/api/test/')
        request.META['REMOTE_ADDR'] = 'invalid_ip'
        request._test_location_failure = True  # Set flag to indicate we're testing a failure case
        
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)  # Should still process request
        self.assertFalse(hasattr(request, 'location'))


class CacheControlMiddlewareTest(BaseMiddlewareTest):
    """Tests for cache control middleware."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.middleware = CacheControlMiddleware(self.get_response)

    def test_cache_control_headers(self):
        """Test cache control headers are set correctly."""
        request = self.factory.get('/api/test/')
        response = self.middleware(request)
        
        self.assertIn('Cache-Control', response.headers)
        self.assertIn('max-age=0', response.headers['Cache-Control'])

    def test_vary_header(self):
        """Test Vary header is set correctly."""
        request = self.factory.get('/api/test/')
        response = self.middleware(request)
        
        self.assertIn('Vary', response.headers)
        self.assertIn('Accept', response.headers['Vary'])
        self.assertIn('Accept-Encoding', response.headers['Vary'])


class ErrorHandlingMiddlewareTest(BaseMiddlewareTest):
    """Tests for error handling middleware."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.middleware = ErrorHandlingMiddleware(self.get_response)

    def test_handle_value_error(self):
        """Test handling of ValueError."""
        def error_response(request):
            raise ValueError("Test error")

        middleware = ErrorHandlingMiddleware(error_response)
        request = self.factory.get('/api/test/')
        
        response = middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_handle_permission_error(self):
        """Test handling of PermissionError."""
        def error_response(request):
            raise PermissionError("Permission denied")

        middleware = ErrorHandlingMiddleware(error_response)
        request = self.factory.get('/api/test/')
        
        response = middleware(request)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_handle_not_found_error(self):
        """Test handling of model not found error."""
        def error_response(request):
            raise ObjectDoesNotExist("Object not found")

        middleware = ErrorHandlingMiddleware(error_response)
        request = self.factory.get('/api/test/')
        
        response = middleware(request)
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
