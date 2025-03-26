"""
Test settings for the coupon_core project.

This module includes configurations for test environments, ensuring proper
database setup and test execution across multiple databases.
"""

import os
from datetime import timedelta
from .base import *  # Import base settings first

# Test Database Router
class TestRouter:
    """
    A router that forces all operations to use the 'default' database during tests.
    This ensures that test data is properly isolated and managed.
    """
    def db_for_read(self, model, **hints):
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True

# Unset environment variables that might interfere with test settings
os.environ.pop('DB_PORT', None)
os.environ.pop('DB_HOST', None)
os.environ.pop('DB_USER', None)
os.environ.pop('DB_PASSWORD', None)
os.environ.pop('POSTGRES_USER', None)
os.environ.pop('POSTGRES_PASSWORD', None)
os.environ.pop('POSTGRES_DB', None)
os.environ.pop('DATABASE_URL', None)

# Debug
DEBUG = False

# Secret Key
SECRET_KEY = "test-secret-key-for-testing-only"

# Set GDAL library path
GDAL_LIBRARY_PATH = '/usr/local/Cellar/gdal/3.10.2_3/lib/libgdal.dylib'

# Use PostgreSQL with PostGIS for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'coupon_db',
        'USER': os.getenv('DB_USER', 'coupon_admin'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'S3cureP@ssw0rd'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    },
    'authentication_shard': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'authentication_shard',
        'USER': os.getenv('DB_USER', 'coupon_admin'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'S3cureP@ssw0rd'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    },
    'geodiscounts_db': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'geodiscounts_db',
        'USER': os.getenv('DB_USER', 'coupon_admin'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'S3cureP@ssw0rd'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    },
    'vector_db': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'vector_db',
        'USER': os.getenv('DB_USER', 'coupon_admin'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'S3cureP@ssw0rd'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Configure migrations for test databases
MIGRATION_MODULES = {}  # Allow all migrations to run

# Use fast password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable celery during tests
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable CSRF checks during tests
MIDDLEWARE = [m for m in MIDDLEWARE if 'csrf' not in m.lower()]

# Configure test-specific database routers
DATABASE_ROUTERS = ['coupon_core.settings.test.TestRouter']

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_OUTPUT_DIR = os.path.join(BASE_DIR, 'test_reports')

# Create test reports directory if it doesn't exist
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

# Required for spatialite
SPATIALITE_LIBRARY_PATH = 'mod_spatialite'

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True

# Use test Redis settings
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 15  # Use a separate DB for tests

# URL Configuration
ROOT_URLCONF = 'coupon_core.urls'

# API URL prefix
API_PREFIX = 'api'
GEODISCOUNTS_API_PREFIX = f'{API_PREFIX}/geodiscounts'

# Use test cache backend
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable throttling during tests
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
}

# SimpleJWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# Use test static file storage
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Allow all hosts during tests
ALLOWED_HOSTS = ['*']

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_OUTPUT_DIR = os.path.join(BASE_DIR, 'test_reports')

# Create test reports directory if it doesn't exist
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

# Required for spatialite
SPATIALITE_LIBRARY_PATH = 'mod_spatialite'

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True 