"""
Test cases for settings configuration.

This module tests:
1. Base settings configuration
2. Environment-specific settings (dev, prod, staging)
3. Security settings
4. Database configuration
5. Third-party integrations
"""

import os
from unittest import TestCase
from unittest.mock import patch
from django.test import override_settings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class BaseSettingsTestCase(TestCase):
    """Test suite for base settings configuration."""

    def test_debug_setting(self):
        """Test DEBUG setting based on environment."""
        with override_settings(DEBUG=True):
            self.assertTrue(settings.DEBUG)
        
        with override_settings(DEBUG=False):
            self.assertFalse(settings.DEBUG)

    def test_allowed_hosts(self):
        """Test ALLOWED_HOSTS configuration."""
        self.assertTrue(isinstance(settings.ALLOWED_HOSTS, list))
        self.assertTrue(all(isinstance(host, str) for host in settings.ALLOWED_HOSTS))

    def test_installed_apps(self):
        """Test required apps are installed."""
        required_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'authentication',
            'geodiscounts',
        ]
        
        for app in required_apps:
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_middleware_configuration(self):
        """Test middleware configuration."""
        required_middleware = [
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ]
        
        for middleware in required_middleware:
            self.assertIn(middleware, settings.MIDDLEWARE)

    def test_database_configuration(self):
        """Test database configuration."""
        self.assertTrue('default' in settings.DATABASES)
        db_config = settings.DATABASES['default']
        self.assertTrue('ENGINE' in db_config)
        self.assertTrue('NAME' in db_config)

    def test_auth_password_validators(self):
        """Test password validation settings."""
        required_validators = [
            'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            'django.contrib.auth.password_validation.MinimumLengthValidator',
            'django.contrib.auth.password_validation.CommonPasswordValidator',
            'django.contrib.auth.password_validation.NumericPasswordValidator',
        ]
        
        for validator in required_validators:
            self.assertTrue(
                any(val['NAME'] == validator for val in settings.AUTH_PASSWORD_VALIDATORS)
            )

class SecuritySettingsTestCase(TestCase):
    """Test suite for security-related settings."""

    def test_secret_key_configuration(self):
        """Test SECRET_KEY configuration."""
        self.assertTrue(hasattr(settings, 'SECRET_KEY'))
        self.assertTrue(len(settings.SECRET_KEY) > 20)

    def test_secure_ssl_settings(self):
        """Test SSL/HTTPS settings in production."""
        if not settings.DEBUG:
            self.assertTrue(settings.SECURE_SSL_REDIRECT)
            self.assertTrue(settings.SECURE_PROXY_SSL_HEADER)
            self.assertTrue(settings.SESSION_COOKIE_SECURE)
            self.assertTrue(settings.CSRF_COOKIE_SECURE)

    def test_csrf_settings(self):
        """Test CSRF protection settings."""
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertTrue(hasattr(settings, 'CSRF_TRUSTED_ORIGINS'))

    def test_cors_settings(self):
        """Test CORS settings configuration."""
        self.assertTrue(hasattr(settings, 'CORS_ALLOWED_ORIGINS'))
        self.assertTrue(isinstance(settings.CORS_ALLOWED_ORIGINS, (list, tuple)))

class StorageSettingsTestCase(TestCase):
    """Test suite for storage settings."""

    def test_static_files_configuration(self):
        """Test static files configuration."""
        self.assertTrue(hasattr(settings, 'STATIC_URL'))
        self.assertTrue(hasattr(settings, 'STATIC_ROOT'))
        self.assertTrue(hasattr(settings, 'STATICFILES_DIRS'))

    def test_media_files_configuration(self):
        """Test media files configuration."""
        self.assertTrue(hasattr(settings, 'MEDIA_URL'))
        self.assertTrue(hasattr(settings, 'MEDIA_ROOT'))

class ThirdPartyIntegrationTestCase(TestCase):
    """Test suite for third-party integration settings."""

    def test_rest_framework_settings(self):
        """Test DRF settings configuration."""
        self.assertTrue(hasattr(settings, 'REST_FRAMEWORK'))
        drf_settings = settings.REST_FRAMEWORK
        
        # Test authentication classes
        self.assertTrue('DEFAULT_AUTHENTICATION_CLASSES' in drf_settings)
        
        # Test permission classes
        self.assertTrue('DEFAULT_PERMISSION_CLASSES' in drf_settings)
        
        # Test pagination settings
        self.assertTrue('DEFAULT_PAGINATION_CLASS' in drf_settings)
        self.assertTrue('PAGE_SIZE' in drf_settings)

    def test_celery_settings(self):
        """Test Celery configuration."""
        self.assertTrue(hasattr(settings, 'CELERY_BROKER_URL'))
        self.assertTrue(hasattr(settings, 'CELERY_RESULT_BACKEND'))
        self.assertTrue(hasattr(settings, 'CELERY_ACCEPT_CONTENT'))
        self.assertTrue(hasattr(settings, 'CELERY_TASK_SERIALIZER'))
        self.assertTrue(hasattr(settings, 'CELERY_RESULT_SERIALIZER'))

    def test_email_settings(self):
        """Test email configuration."""
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
        self.assertTrue(hasattr(settings, 'EMAIL_HOST'))
        self.assertTrue(hasattr(settings, 'EMAIL_PORT'))
        self.assertTrue(hasattr(settings, 'EMAIL_USE_TLS'))

class EnvironmentSpecificSettingsTestCase(TestCase):
    """Test suite for environment-specific settings."""

    @patch('os.getenv')
    def test_development_settings(self, mock_getenv):
        """Test development environment settings."""
        mock_getenv.return_value = 'development'
        
        from coupon_core.settings import dev
        
        self.assertTrue(dev.DEBUG)
        self.assertEqual(dev.ALLOWED_HOSTS, ['*'])
        self.assertTrue(isinstance(dev.DATABASES['default'], dict))

    @patch('os.getenv')
    def test_production_settings(self, mock_getenv):
        """Test production environment settings."""
        mock_getenv.return_value = 'production'
        
        from coupon_core.settings import prod
        
        self.assertFalse(prod.DEBUG)
        self.assertTrue(len(prod.ALLOWED_HOSTS) > 0)
        self.assertTrue(isinstance(prod.DATABASES['default'], dict))

    @patch('os.getenv')
    def test_staging_settings(self, mock_getenv):
        """Test staging environment settings."""
        mock_getenv.return_value = 'staging'
        
        from coupon_core.settings import staging
        
        self.assertTrue(isinstance(staging.DATABASES['default'], dict))
        self.assertTrue(hasattr(staging, 'STATIC_ROOT'))
        self.assertTrue(hasattr(staging, 'MEDIA_ROOT')) 