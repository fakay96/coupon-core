"""Page validation middleware for Scrapy.

This module provides middleware for validating and handling page requests.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional, Set
from scrapy.http import Request, Response
from urllib.parse import urlparse, parse_qs

LOGGER: logging.Logger = logging.getLogger(__name__)

class PageValidationMiddleware:
    """Middleware to validate and handle non-existent pages."""
    
    def __init__(self) -> None:
        """Initialize the middleware."""
        self.max_page: Dict[str, int] = {}  # Store max valid page for each spider
        self.invalid_pages: Dict[str, Set[int]] = {}  # Track invalid pages per spider

    def process_request(self, request: Request, spider: Any) -> Optional[Response]:
        """Validate the request before it's processed.
        
        Args:
            request: The request to validate
            spider: The spider making the request
            
        Returns:
            Optional[Response]: A 404 response if the page is invalid, None otherwise
        """
        # Skip validation for non-pagination requests
        if 'page' not in request.url:
            return None

        spider_name = spider.name
        if spider_name not in self.invalid_pages:
            self.invalid_pages[spider_name] = set()

        # Extract page number from URL
        parsed = urlparse(request.url)
        query_params = parse_qs(parsed.query)
        page_num = int(query_params.get('page', ['1'])[0])

        # Check if we've already determined this page is invalid
        if page_num in self.invalid_pages[spider_name]:
            LOGGER.info(f"Skipping known invalid page {page_num} for {spider_name}")
            return Response(request.url, status=404)

        # If we have a max page and this request is beyond it
        if spider_name in self.max_page and page_num > self.max_page[spider_name]:
            LOGGER.info(f"Skipping page {page_num} beyond max page {self.max_page[spider_name]} for {spider_name}")
            return Response(request.url, status=404)

        return None

    def process_response(self, request: Request, response: Response, spider: Any) -> Response:
        """Process the response and update page validation info.
        
        Args:
            request: The original request
            response: The response to process
            spider: The spider making the request
            
        Returns:
            Response: The processed response
        """
        spider_name = spider.name
        
        # Skip non-pagination responses
        if 'page' not in request.url:
            return response

        # Extract page number from URL
        parsed = urlparse(request.url)
        query_params = parse_qs(parsed.query)
        page_num = int(query_params.get('page', ['1'])[0])

        # If we get a 404, mark this page and previous pages as invalid
        if response.status == 404:
            self.invalid_pages[spider_name].add(page_num)
            
            # Update max valid page if this is the first invalid page we've found
            if spider_name not in self.max_page or page_num - 1 > self.max_page[spider_name]:
                self.max_page[spider_name] = page_num - 1
                LOGGER.info(f"Updated max valid page for {spider_name} to {self.max_page[spider_name]}")

        return response 