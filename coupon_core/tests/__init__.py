"""
Test configuration for coupon_core.

This module ensures that all tests in the test suite are discovered and run.
"""

from django.conf import settings
import os

# Ensure test settings are used
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon_core.settings.test')

# Import all test modules to ensure they are discovered
from .settings.test_settings import *
from .middlewares.test_middlewares import *
from .middlewares.test_middleware_security import *
from .urls.test_urls import *
from .server.test_server import *
from .celery.test_celery import *
