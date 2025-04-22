"""Proxy middleware package for Scrapy.

This package provides middleware for handling proxy-related functionality.
"""

from .authenticated import AuthenticatedProxyMiddleware
from .health import ProxyHealthTracker

__all__ = ['AuthenticatedProxyMiddleware', 'ProxyHealthTracker'] 