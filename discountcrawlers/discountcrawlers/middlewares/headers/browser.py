"""Browser header middleware for Scrapy.

This module provides middleware for handling browser-like headers.
"""

from __future__ import annotations
from typing import Any
from scrapy.http import Request
from random import choice

class FakeBrowserHeaderMiddleware:
    """Downloader middleware to randomize User-Agent headers."""
    
    USER_AGENTS: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    ]

    def process_request(self, request: Request, spider: Any) -> None:
        """Set a random User-Agent header on each request.
        
        Args:
            request: The request to process
            spider: The spider making the request
        """
        request.headers["User-Agent"] = choice(self.USER_AGENTS) 