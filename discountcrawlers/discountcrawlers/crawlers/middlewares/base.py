"""Base middleware class for all discount crawlers."""

from typing import Dict, Any, Optional
import logging
from scrapy import signals
from scrapy.http import Request, Response

LOGGER = logging.getLogger(__name__)

class DiscountMiddleware:
    """Base middleware class for all discount crawlers.
    
    This class provides common functionality and configuration for all discount middlewares.
    """
    
    def __init__(self, crawler):
        """Initialize the middleware.
        
        Args:
            crawler: The crawler instance
        """
        self.crawler = crawler
        self.settings = crawler.settings
        
    @classmethod
    def from_crawler(cls, crawler):
        """Create a middleware instance from a crawler.
        
        Args:
            crawler: The crawler instance
            
        Returns:
            DiscountMiddleware: Middleware instance
        """
        middleware = cls(crawler)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
        
    def process_request(self, request: Request, spider) -> Optional[Response]:
        """Process a request.
        
        Args:
            request: The request to process
            spider: The spider making the request
            
        Returns:
            Optional[Response]: Response if the request should be handled, None otherwise
        """
        return None
        
    def process_response(self, request: Request, response: Response, spider) -> Response:
        """Process a response.
        
        Args:
            request: The request that generated the response
            response: The response to process
            spider: The spider that received the response
            
        Returns:
            Response: The processed response
        """
        return response
        
    def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Response]:
        """Process an exception.
        
        Args:
            request: The request that generated the exception
            exception: The exception to process
            spider: The spider that received the exception
            
        Returns:
            Optional[Response]: Response if the exception should be handled, None otherwise
        """
        return None
        
    def spider_opened(self, spider):
        """Handle spider opened signal.
        
        Args:
            spider: The spider instance that was opened
        """
        LOGGER.info(f"Spider {spider.name} opened")
        
    def spider_closed(self, spider):
        """Handle spider closed signal.
        
        Args:
            spider: The spider instance that was closed
        """
        LOGGER.info(f"Spider {spider.name} closed") 