"""Authenticated proxy middleware for Scrapy.

This module provides middleware for handling authenticated proxy requests.
"""

from __future__ import annotations
import logging
from typing import Any, Optional
from scrapy import signals
from scrapy.http import Request, Response
import requests
from .health import ProxyHealthTracker

LOGGER: logging.Logger = logging.getLogger(__name__)

class AuthenticatedProxyMiddleware:
    """Downloader middleware to apply authenticated proxies."""
    
    def __init__(self, proxy_url: str, username: str, password: str) -> None:
        """Initialize the middleware with proxy credentials.
        
        Args:
            proxy_url: URL to fetch proxy from
            username: Proxy authentication username
            password: Proxy authentication password
        """
        self.proxy_url = proxy_url
        self.username = username
        self.password = password
        self.tracker = ProxyHealthTracker()

    @classmethod
    def from_crawler(cls, crawler: Any) -> AuthenticatedProxyMiddleware:
        """Instantiate from crawler settings.
        
        Args:
            crawler: Scrapy crawler instance
            
        Returns:
            An instance of the middleware
        """
        inst = cls(
            proxy_url=crawler.settings.get("PROXY_URL", ""),
            username=crawler.settings.get("PROXY_USER", ""),
            password=crawler.settings.get("PROXY_PASS", ""),
        )
        crawler.signals.connect(inst.spider_closed, signal=signals.spider_closed)
        return inst

    def process_request(self, request: Request, spider: Any) -> None:
        """Attach proxy to request by fetching from PROXY_URL.
        
        Args:
            request: The request to process
            spider: The spider making the request
        """
        if not self.proxy_url:
            return
        try:
            resp = requests.get(self.proxy_url, auth=(self.username, self.password), timeout=10)
            resp.raise_for_status()
            proxy = resp.text.strip()
            request.meta["proxy"] = f"http://{proxy}"
            self.tracker.record("authenticated", True)
        except Exception as exc:
            LOGGER.error("Proxy fetch failed: %s", exc)
            self.tracker.record("authenticated", False)

    def process_response(self, request: Request, response: Response, spider: Any) -> Response:
        """Record response health for the proxy.
        
        Args:
            request: The original request
            response: The response to process
            spider: The spider making the request
            
        Returns:
            The processed response
        """
        success = response.status == 200
        self.tracker.record("authenticated", success)
        return response

    def spider_closed(self, spider: Any) -> None:
        """Report proxy health when spider finishes.
        
        Args:
            spider: The spider that closed
        """
        self.tracker.report(spider) 