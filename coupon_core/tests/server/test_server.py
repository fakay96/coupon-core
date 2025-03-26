"""
Test cases for WSGI and ASGI server configuration.

This module tests:
1. WSGI application configuration
2. ASGI application configuration
3. Server middleware
4. Static file handling
"""

from django.test import TestCase
from django.core.handlers.wsgi import WSGIHandler
from django.core.handlers.asgi import ASGIHandler
from django.conf import settings
from unittest.mock import patch, Mock
import os
from coupon_core.wsgi import application as wsgi_app
from coupon_core.asgi import application as asgi_app

class WSGIConfigTestCase(TestCase):
    """Test suite for WSGI configuration."""

    def test_wsgi_application(self):
        """Test WSGI application configuration."""
        self.assertIsInstance(wsgi_app, WSGIHandler)
        self.assertEqual(os.environ.get('DJANGO_SETTINGS_MODULE'), 'coupon_core.settings')

    def test_wsgi_middleware_stack(self):
        """Test WSGI middleware stack."""
        middleware = wsgi_app.get_response.middleware
        self.assertTrue(len(middleware) > 0)
        
        # Test specific middleware presence
        middleware_classes = [m.__class__.__name__ for m in middleware]
        self.assertIn('SecurityMiddleware', middleware_classes)
        self.assertIn('SessionMiddleware', middleware_classes)
        self.assertIn('CommonMiddleware', middleware_classes)

    @patch('django.core.handlers.wsgi.WSGIHandler.__call__')
    def test_wsgi_request_handling(self, mock_call):
        """Test WSGI request handling."""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'wsgi.url_scheme': 'http',
            'wsgi.input': Mock(),
            'wsgi.errors': Mock(),
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': '80',
        }
        
        start_response = Mock()
        wsgi_app(environ, start_response)
        mock_call.assert_called_once()

    def test_wsgi_settings(self):
        """Test WSGI-specific settings."""
        self.assertTrue(hasattr(settings, 'WSGI_APPLICATION'))
        self.assertEqual(settings.WSGI_APPLICATION, 'coupon_core.wsgi.application')

class ASGIConfigTestCase(TestCase):
    """Test suite for ASGI configuration."""

    def test_asgi_application(self):
        """Test ASGI application configuration."""
        self.assertIsInstance(asgi_app, ASGIHandler)
        self.assertEqual(os.environ.get('DJANGO_SETTINGS_MODULE'), 'coupon_core.settings')

    def test_asgi_middleware_stack(self):
        """Test ASGI middleware stack."""
        middleware = asgi_app.get_response.middleware
        self.assertTrue(len(middleware) > 0)
        
        # Test specific middleware presence
        middleware_classes = [m.__class__.__name__ for m in middleware]
        self.assertIn('SecurityMiddleware', middleware_classes)
        self.assertIn('SessionMiddleware', middleware_classes)
        self.assertIn('CommonMiddleware', middleware_classes)

    @patch('django.core.handlers.asgi.ASGIHandler.__call__')
    async def test_asgi_request_handling(self, mock_call):
        """Test ASGI request handling."""
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/',
            'query_string': b'',
            'headers': [],
            'client': ('127.0.0.1', 50000),
            'server': ('testserver', 80),
        }
        
        receive = Mock()
        send = Mock()
        
        await asgi_app(scope, receive, send)
        mock_call.assert_called_once()

    def test_asgi_settings(self):
        """Test ASGI-specific settings."""
        self.assertTrue(hasattr(settings, 'ASGI_APPLICATION'))
        self.assertEqual(settings.ASGI_APPLICATION, 'coupon_core.asgi.application')

class StaticFileHandlingTestCase(TestCase):
    """Test suite for static file handling configuration."""

    def test_static_file_handlers(self):
        """Test static file handler configuration."""
        self.assertTrue(hasattr(settings, 'STATICFILES_HANDLERS'))
        handlers = getattr(settings, 'STATICFILES_HANDLERS', [])
        self.assertTrue(len(handlers) > 0)

    def test_static_file_finders(self):
        """Test static file finder configuration."""
        self.assertTrue(hasattr(settings, 'STATICFILES_FINDERS'))
        finders = settings.STATICFILES_FINDERS
        self.assertTrue(len(finders) > 0)
        
        required_finders = [
            'django.contrib.staticfiles.finders.FileSystemFinder',
            'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        ]
        for finder in required_finders:
            self.assertIn(finder, finders)

    def test_static_file_storage(self):
        """Test static file storage configuration."""
        self.assertTrue(hasattr(settings, 'STATICFILES_STORAGE'))
        self.assertTrue(hasattr(settings, 'DEFAULT_FILE_STORAGE'))

    @override_settings(DEBUG=True)
    def test_static_serving_development(self):
        """Test static file serving in development."""
        self.assertTrue(settings.DEBUG)
        self.assertTrue('django.contrib.staticfiles' in settings.INSTALLED_APPS)
        
        # Test static URL patterns
        from django.conf.urls.static import static
        urlpatterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        self.assertTrue(len(urlpatterns) > 0)

    def test_manifest_storage(self):
        """Test manifest storage configuration."""
        if not settings.DEBUG:
            self.assertTrue(
                'django.contrib.staticfiles.storage.ManifestStaticFilesStorage' in 
                settings.STATICFILES_STORAGE
            ) 