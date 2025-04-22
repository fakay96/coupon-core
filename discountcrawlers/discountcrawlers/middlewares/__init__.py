"""Middleware package for Scrapy.

This package provides various middleware components for the discount crawlers.
"""

from .proxy import AuthenticatedProxyMiddleware
from .headers import FakeBrowserHeaderMiddleware
from .validation import PageValidationMiddleware
from .pagination.penny import PennyPaginationMiddleware

__all__ = [
    'AuthenticatedProxyMiddleware',
    'FakeBrowserHeaderMiddleware',
    'PageValidationMiddleware',
    'PennyPaginationMiddleware',
] 