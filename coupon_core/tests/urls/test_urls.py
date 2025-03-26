"""
Test cases for URL configuration.

This module tests:
1. URL patterns and routing
2. Admin site URLs
3. API endpoints
4. Static/Media file serving
5. Debug toolbar URLs (in development)
"""

from django.test import TestCase, override_settings
from django.urls import reverse, resolve, NoReverseMatch
from django.conf import settings
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()

class URLPatternsTestCase(TestCase):
    """Test suite for URL patterns."""

    def setUp(self):
        """Set up test environment."""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

    def test_admin_urls(self):
        """Test admin site URLs."""
        admin_urls = [
            'admin:index',
            'admin:login',
            'admin:logout',
            'admin:password_change',
            'admin:password_change_done',
        ]
        
        for url_name in admin_urls:
            try:
                url = reverse(url_name)
                resolver = resolve(url)
                self.assertEqual(resolver.namespace, 'admin')
            except NoReverseMatch:
                self.fail(f"Could not reverse URL: {url_name}")

    def test_api_root_url(self):
        """Test API root URL."""
        url = reverse('api-root')
        resolver = resolve(url)
        self.assertEqual(resolver.view_name, 'api-root')

    def test_auth_api_urls(self):
        """Test authentication API URLs."""
        auth_urls = [
            'auth:login',
            'auth:register',
            'auth:logout',
            'auth:password-reset',
            'auth:password-reset-confirm',
            'auth:verify-email',
        ]
        
        for url_name in auth_urls:
            try:
                url = reverse(url_name)
                resolver = resolve(url)
                self.assertEqual(resolver.namespace, 'auth')
            except NoReverseMatch:
                self.fail(f"Could not reverse URL: {url_name}")

    def test_static_media_urls(self):
        """Test static and media file URLs."""
        self.assertTrue(settings.STATIC_URL.startswith('/'))
        self.assertTrue(settings.MEDIA_URL.startswith('/'))

    @override_settings(DEBUG=True)
    def test_debug_toolbar_url(self):
        """Test debug toolbar URL configuration in development."""
        if 'debug_toolbar' in settings.INSTALLED_APPS:
            try:
                url = reverse('djdt:render_panel')
                resolver = resolve(url)
                self.assertEqual(resolver.namespace, 'djdt')
            except NoReverseMatch:
                self.fail("Could not reverse debug toolbar URL")

class APIEndpointsTestCase(APITestCase):
    """Test suite for API endpoints."""

    def setUp(self):
        """Set up test environment."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_api_root_endpoint(self):
        """Test API root endpoint."""
        response = self.client.get(reverse('api-root'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, dict))

    def test_auth_endpoints(self):
        """Test authentication endpoints."""
        # Test login endpoint
        login_url = reverse('auth:login')
        response = self.client.post(login_url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('token' in response.data)

        # Test logout endpoint
        logout_url = reverse('auth:logout')
        response = self.client.post(logout_url)
        self.assertEqual(response.status_code, 200)

        # Test register endpoint
        register_url = reverse('auth:register')
        response = self.client.post(register_url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123'
        })
        self.assertEqual(response.status_code, 201)

    def test_protected_endpoints(self):
        """Test protected API endpoints."""
        # Test with authenticated user
        protected_url = reverse('auth:profile')
        response = self.client.get(protected_url)
        self.assertEqual(response.status_code, 200)

        # Test with unauthenticated user
        self.client.force_authenticate(user=None)
        response = self.client.get(protected_url)
        self.assertEqual(response.status_code, 401)

    def test_admin_api_endpoints(self):
        """Test admin API endpoints."""
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Test with admin user
        self.client.force_authenticate(user=admin_user)
        admin_url = reverse('auth:admin-users')
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)

        # Test with non-admin user
        self.client.force_authenticate(user=self.user)
        response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 403)

class URLConfigurationTestCase(TestCase):
    """Test suite for URL configuration settings."""

    def test_root_urlconf_setting(self):
        """Test ROOT_URLCONF setting."""
        self.assertTrue(hasattr(settings, 'ROOT_URLCONF'))
        self.assertEqual(settings.ROOT_URLCONF, 'coupon_core.urls')

    def test_append_slash_setting(self):
        """Test APPEND_SLASH setting."""
        self.assertTrue(hasattr(settings, 'APPEND_SLASH'))
        self.assertIsInstance(settings.APPEND_SLASH, bool)

    def test_prepend_www_setting(self):
        """Test PREPEND_WWW setting."""
        self.assertTrue(hasattr(settings, 'PREPEND_WWW'))
        self.assertIsInstance(settings.PREPEND_WWW, bool)

    @override_settings(DEBUG=True)
    def test_debug_url_settings(self):
        """Test debug-specific URL settings."""
        self.assertTrue(hasattr(settings, 'DEBUG'))
        if settings.DEBUG:
            self.assertTrue(hasattr(settings, 'INTERNAL_IPS'))
            self.assertIsInstance(settings.INTERNAL_IPS, (list, tuple)) 