from typing import Any, AsyncGenerator, Dict, Optional, Union
from scrapy import Spider
from scrapy.http import Request, Response
from scrapy.middleware import MiddlewareManager
from scrapy.utils.misc import load_object
from scrapy.utils.python import to_bytes
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BasePaginationMiddleware(ABC):
    """Base class for pagination middlewares.
    
    This class provides a foundation for implementing pagination in Scrapy spiders.
    Specific pagination logic should be implemented in subclasses.
    """
    
    def __init__(self, settings: Dict[str, Any]) -> None:
        """Initialize the middleware with settings.
        
        Args:
            settings: Scrapy settings dictionary
        """
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @classmethod
    def from_crawler(cls, crawler):
        """Create middleware instance from crawler.
        
        Args:
            crawler: The crawler instance
            
        Returns:
            An instance of the middleware
        """
        return cls(crawler.settings)
    
    @abstractmethod
    async def should_paginate(self, response: Response, spider: Spider) -> bool:
        """Determine if pagination should be attempted for this response.
        
        Args:
            response: The response to check
            spider: The spider making the request
            
        Returns:
            bool: True if pagination should be attempted, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_next_page_url(self, response: Response, spider: Spider) -> Optional[str]:
        """Extract the URL for the next page.
        
        Args:
            response: The current response
            spider: The spider making the request
            
        Returns:
            Optional[str]: The URL for the next page if found, None otherwise
        """
        pass
    
    async def process_spider_output(
        self,
        response: Response,
        result: Union[AsyncGenerator, list],
        spider: Spider
    ) -> AsyncGenerator:
        """Process spider output and handle pagination.
        
        This method yields all items from the spider and attempts pagination
        if appropriate.
        
        Args:
            response: The response being processed
            result: The spider's output (items/requests)
            spider: The spider instance
            
        Yields:
            Items and requests, including pagination requests if appropriate
        """
        # First yield all the original items/requests
        async for item_or_request in result:
            yield item_or_request
            
        try:
            # Check if we should attempt pagination
            should_paginate = await self.should_paginate(response, spider)
            if should_paginate:
                next_url = await self.get_next_page_url(response, spider)
                if next_url:
                    # Create a new request for the next page
                    yield Request(
                        url=next_url,
                        callback=response.request.callback,
                        meta=response.request.meta,
                        dont_filter=True
                    )
        except Exception as e:
            logger.error(f"Error during pagination: {e}") 