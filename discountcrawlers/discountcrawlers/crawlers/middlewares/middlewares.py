"""Custom spider and downloader middlewares.

This module re-exports middleware components from their respective packages.
"""

from .middlewares.proxy import AuthenticatedProxyMiddleware
from .middlewares.headers import FakeBrowserHeaderMiddleware
from .middlewares.validation import PageValidationMiddleware
from .middlewares.pagination.penny import PennyPaginationMiddleware

__all__ = [
    'AuthenticatedProxyMiddleware',
    'FakeBrowserHeaderMiddleware',
    'PageValidationMiddleware',
    'PennyPaginationMiddleware',
]
