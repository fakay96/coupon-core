"""
Test cases for authentication routers.

This module tests:
1. URL routing
2. View registration
3. Router configuration
4. Default routing behavior
"""

from django.test import TestCase
from django.urls import reverse, resolve
from rest_framework.test import APITestCase
from rest_framework import status

from authentication.routers import AuthRouter
from authentication.v1.views.userprofile_views import UserProfileView
from authentication.v1.views.authentication_views import (
    LoginView,
    RegisterView,
    GuestTokenView
)


class AuthRouterTestCase(TestCase):
    """Test suite for authentication router configuration."""

    def setUp(self):
        """Set up router for testing."""
        self.router = AuthRouter()
        self.router.register()  # Register all views

    def test_router_registration(self):
        """
        Test view registration in router.

        Expected:
            - All views are registered
            - URLs are generated correctly
            - View names are set properly
        """
        # Verify views are registered
        registered_views = self.router.registry
        self.assertTrue(any(view[1].__name__ == 'UserProfileView' for view in registered_views))
        self.assertTrue(any(view[1].__name__ == 'LoginView' for view in registered_views))
        self.assertTrue(any(view[1].__name__ == 'RegisterView' for view in registered_views))

    def test_url_pattern_generation(self):
        """
        Test URL pattern generation.

        Expected:
            - URL patterns are generated correctly
            - Patterns include API version
            - Patterns are properly namespaced
        """
        urls = self.router.urls
        self.assertTrue(any('v1' in url.pattern.regex.pattern for url in urls))
        self.assertTrue(any('profile' in url.pattern.regex.pattern for url in urls))
        self.assertTrue(any('login' in url.pattern.regex.pattern for url in urls))

    def test_default_base_name(self):
        """
        Test default base name generation.

        Expected:
            - Base names are generated correctly
            - Names follow convention
        """
        base_name = self.router.get_default_base_name(UserProfileView)
        self.assertEqual(base_name, 'userprofile')

    def test_router_lookup_patterns(self):
        """
        Test router lookup patterns.

        Expected:
            - Lookup patterns are correct
            - URL parameters are handled properly
        """
        lookup_pattern = self.router.get_lookup_regex('pk')
        self.assertIn('pk', lookup_pattern)
        self.assertTrue(lookup_pattern.startswith('(?P<'))


class AuthURLsTestCase(APITestCase):
    """Test suite for authentication URLs."""

    def test_login_url_resolves(self):
        """
        Test login URL resolution.

        Expected:
            - URL resolves to correct view
            - View name matches
            - URL pattern is correct
        """
        url = reverse('v1:login')
        resolved = resolve(url)
        self.assertEqual(resolved.func.cls, LoginView)
        self.assertEqual(url, '/authentication/api/v1/login/')

    def test_register_url_resolves(self):
        """
        Test register URL resolution.

        Expected:
            - URL resolves to correct view
            - View name matches
            - URL pattern is correct
        """
        url = reverse('v1:register')
        resolved = resolve(url)
        self.assertEqual(resolved.func.cls, RegisterView)
        self.assertEqual(url, '/authentication/api/v1/register/')

    def test_profile_url_resolves(self):
        """
        Test profile URL resolution.

        Expected:
            - URL resolves to correct view
            - View name matches
            - URL pattern is correct
        """
        url = reverse('v1:userprofile')
        resolved = resolve(url)
        self.assertEqual(resolved.func.cls, UserProfileView)
        self.assertEqual(url, '/authentication/api/v1/profile/')

    def test_guest_token_url_resolves(self):
        """
        Test guest token URL resolution.

        Expected:
            - URL resolves to correct view
            - View name matches
            - URL pattern is correct
        """
        url = reverse('v1:guest-token')
        resolved = resolve(url)
        self.assertEqual(resolved.func.cls, GuestTokenView)
        self.assertEqual(url, '/authentication/api/v1/guest-token/')

    def test_url_names_unique(self):
        """
        Test URL name uniqueness.

        Expected:
            - All URL names are unique
            - No naming conflicts
        """
        urls = [
            reverse('v1:login'),
            reverse('v1:register'),
            reverse('v1:userprofile'),
            reverse('v1:guest-token')
        ]
        self.assertEqual(len(urls), len(set(urls)))

    def test_url_version_prefix(self):
        """
        Test URL version prefixing.

        Expected:
            - All URLs have version prefix
            - Version format is correct
        """
        urls = [
            reverse('v1:login'),
            reverse('v1:register'),
            reverse('v1:userprofile'),
            reverse('v1:guest-token')
        ]
        for url in urls:
            self.assertIn('/v1/', url)

    def test_trailing_slashes(self):
        """
        Test URL trailing slashes.

        Expected:
            - All URLs end with slash
            - Consistent URL format
        """
        urls = [
            reverse('v1:login'),
            reverse('v1:register'),
            reverse('v1:userprofile'),
            reverse('v1:guest-token')
        ]
        for url in urls:
            self.assertTrue(url.endswith('/'))

    def test_api_prefix(self):
        """
        Test API URL prefix.

        Expected:
            - All URLs have API prefix
            - Prefix format is correct
        """
        urls = [
            reverse('v1:login'),
            reverse('v1:register'),
            reverse('v1:userprofile'),
            reverse('v1:guest-token')
        ]
        for url in urls:
            self.assertIn('/api/', url)

    def test_url_method_not_allowed(self):
        """
        Test URL method restrictions.

        Expected:
            - Incorrect HTTP methods return 405
            - Allowed methods are properly set
        """
        # Test POST-only endpoints with GET
        response = self.client.get(reverse('v1:login'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.get(reverse('v1:register'))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_url_authentication_required(self):
        """
        Test URL authentication requirements.

        Expected:
            - Protected URLs require authentication
            - Public URLs are accessible
        """
        # Test protected endpoint
        response = self.client.get(reverse('v1:userprofile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Public endpoints should be accessible
        response = self.client.post(reverse('v1:guest-token'), {'email': 'test@example.com'})
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 