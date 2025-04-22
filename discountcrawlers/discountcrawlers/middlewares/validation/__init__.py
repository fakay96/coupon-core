"""Validation middleware package for Scrapy.

This package provides middleware for validating requests and responses.
"""

from .page import PageValidationMiddleware

__all__ = ['PageValidationMiddleware'] 