"""Headers middleware package for Scrapy.

This package provides middleware for handling HTTP headers.
"""

from .browser import FakeBrowserHeaderMiddleware

__all__ = ['FakeBrowserHeaderMiddleware'] 