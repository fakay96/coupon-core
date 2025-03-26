"""
Test cases for middleware security features.

This module tests:
1. Security middleware configuration
2. CORS middleware
3. Rate limiting
4. Session security
5. XSS protection
"""

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.conf import settings
from unittest.mock import Mock, patch
from django.middleware.security import SecurityMiddleware
from django.middleware.csrf import CsrfViewMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache

User = get_user_model()

class SecurityMiddlewareTestCase(TestCase):
    """Test suite for security middleware."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.security_middleware = SecurityMiddleware(get_response=Mock())
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_secure_ssl_redirect(self):
        """Test SSL redirect functionality."""
        request = self.factory.get('/', secure=False)
        with override_settings(SECURE_SSL_REDIRECT=True):
            response = self.security_middleware(request)
            self.assertEqual(response.status_code, 301)
            self.assertTrue(response['Location'].startswith('https://'))

    def test_hsts_header(self):
        """Test HTTP Strict Transport Security header."""
        request = self.factory.get('/', secure=True)
        with override_settings(
            SECURE_HSTS_SECONDS=31536000,
            SECURE_HSTS_INCLUDE_SUBDOMAINS=True
        ):
            response = HttpResponse()
            self.security_middleware.process_response(request, response)
            self.assertTrue('Strict-Transport-Security' in response)

    def test_content_type_nosniff(self):
        """Test X-Content-Type-Options nosniff header."""
        request = self.factory.get('/')
        with override_settings(SECURE_CONTENT_TYPE_NOSNIFF=True):
            response = HttpResponse()
            self.security_middleware.process_response(request, response)
            self.assertEqual(
                response['X-Content-Type-Options'],
                'nosniff'
            )

    def test_xss_filter(self):
        """Test X-XSS-Protection header."""
        request = self.factory.get('/')
        with override_settings(SECURE_BROWSER_XSS_FILTER=True):
            response = HttpResponse()
            self.security_middleware.process_response(request, response)
            self.assertEqual(
                response['X-XSS-Protection'],
                '1; mode=block'
            )

    def test_referrer_policy(self):
        """Test Referrer-Policy header."""
        request = self.factory.get('/')
        with override_settings(SECURE_REFERRER_POLICY='same-origin'):
            response = HttpResponse()
            self.security_middleware.process_response(request, response)
            self.assertEqual(
                response['Referrer-Policy'],
                'same-origin'
            )

class CORSMiddlewareTestCase(TestCase):
    """Test suite for CORS middleware."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()

    def test_cors_headers(self):
        """Test CORS headers in response."""
        with override_settings(
            CORS_ALLOW_ALL_ORIGINS=False,
            CORS_ALLOWED_ORIGINS=['https://example.com']
        ):
            request = self.factory.get('/')
            request.META['HTTP_ORIGIN'] = 'https://example.com'
            response = HttpResponse()
            
            # Process CORS headers
            from corsheaders.middleware import CorsMiddleware
            middleware = CorsMiddleware(get_response=lambda r: response)
            response = middleware(request)
            
            self.assertEqual(
                response['Access-Control-Allow-Origin'],
                'https://example.com'
            )

    def test_cors_preflight(self):
        """Test CORS preflight requests."""
        with override_settings(
            CORS_ALLOW_ALL_ORIGINS=False,
            CORS_ALLOWED_ORIGINS=['https://example.com']
        ):
            request = self.factory.options('/')
            request.META['HTTP_ORIGIN'] = 'https://example.com'
            request.META['HTTP_ACCESS_CONTROL_REQUEST_METHOD'] = 'POST'
            response = HttpResponse()
            
            # Process CORS headers
            from corsheaders.middleware import CorsMiddleware
            middleware = CorsMiddleware(get_response=lambda r: response)
            response = middleware(request)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response['Access-Control-Allow-Origin'],
                'https://example.com'
            )

class RateLimitingTestCase(TestCase):
    """Test suite for rate limiting middleware."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        cache.clear()

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        from django_ratelimit.middleware import RatelimitMiddleware
        middleware = RatelimitMiddleware(get_response=Mock())

        # Test within rate limit
        for _ in range(100):
            request = self.factory.get('/')
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            response = middleware(request)
            self.assertNotEqual(response.status_code, 429)

        # Test exceeding rate limit
        with override_settings(RATELIMIT_ENABLE=True):
            request = self.factory.get('/')
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            response = middleware(request)
            self.assertEqual(response.status_code, 429)

    def test_rate_limit_bypass(self):
        """Test rate limit bypass for whitelisted IPs."""
        from django_ratelimit.middleware import RatelimitMiddleware
        middleware = RatelimitMiddleware(get_response=Mock())

        with override_settings(RATELIMIT_ENABLE=True, INTERNAL_IPS=['127.0.0.1']):
            request = self.factory.get('/')
            request.META['REMOTE_ADDR'] = '127.0.0.1'
            response = middleware(request)
            self.assertNotEqual(response.status_code, 429)

class SessionSecurityTestCase(TestCase):
    """Test suite for session security."""

    def setUp(self):
        """Set up test environment."""
        self.factory = RequestFactory()
        self.session_middleware = SessionMiddleware(get_response=Mock())
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_session_cookie_secure(self):
        """Test secure session cookie setting."""
        request = self.factory.get('/')
        self.session_middleware.process_request(request)
        
        with override_settings(SESSION_COOKIE_SECURE=True):
            response = HttpResponse()
            self.session_middleware.process_response(request, response)
            self.assertTrue(response.cookies['sessionid']['secure'])

    def test_session_cookie_httponly(self):
        """Test HttpOnly session cookie setting."""
        request = self.factory.get('/')
        self.session_middleware.process_request(request)
        
        with override_settings(SESSION_COOKIE_HTTPONLY=True):
            response = HttpResponse()
            self.session_middleware.process_response(request, response)
            self.assertTrue(response.cookies['sessionid']['httponly'])

    def test_session_cookie_samesite(self):
        """Test SameSite session cookie setting."""
        request = self.factory.get('/')
        self.session_middleware.process_request(request)
        
        with override_settings(SESSION_COOKIE_SAMESITE='Strict'):
            response = HttpResponse()
            self.session_middleware.process_response(request, response)
            self.assertEqual(
                response.cookies['sessionid']['samesite'],
                'Strict'
            )

    def test_session_expiry(self):
        """Test session expiry settings."""
        request = self.factory.get('/')
        self.session_middleware.process_request(request)
        
        with override_settings(SESSION_COOKIE_AGE=1800):  # 30 minutes
            response = HttpResponse()
            self.session_middleware.process_response(request, response)
            self.assertEqual(
                response.cookies['sessionid']['max-age'],
                1800
            ) 