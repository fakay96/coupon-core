from typing import Any, Dict, Optional
from scrapy import Spider
from scrapy.http import Response
from .base import BasePaginationMiddleware
import logging

logger = logging.getLogger(__name__)

class PennyPaginationMiddleware(BasePaginationMiddleware):
    """Pagination middleware specifically for Penny.de website.
    
    This middleware handles the pagination logic for Penny.de's discount pages.
    It looks for the "Weiter" button and extracts the next page URL from it.
    """
    
    async def should_paginate(self, response: Response, spider: Spider) -> bool:
        """Determine if pagination should be attempted for this response.
        
        For Penny.de, we check if there's a "Weiter" button present on the page.
        
        Args:
            response: The response to check
            spider: The spider making the request
            
        Returns:
            bool: True if pagination should be attempted, False otherwise
        """
        # Check if we're on a valid page and if there's a "Weiter" button
        page = response.meta.get("playwright_page")
        if not page:
            return False
            
        try:
            # Check for the "Weiter" button using first() to get a single element
            weiter_button = page.locator('button:has-text("Weiter")').first
            # Wait for the button to be visible (with timeout)
            await weiter_button.wait_for(timeout=5000)
            return True
        except Exception as e:
            logger.debug(f"No next page button found: {e}")
            return False
    
    async def get_next_page_url(self, response: Response, spider: Spider) -> Optional[str]:
        """Extract the URL for the next page.
        
        For Penny.de, we get the URL from the "Weiter" button's onclick attribute.
        
        Args:
            response: The current response
            spider: The spider making the request
            
        Returns:
            Optional[str]: The URL for the next page if found, None otherwise
        """
        page = response.meta.get("playwright_page")
        if not page:
            return None
            
        try:
            # Get the "Weiter" button using first() to get a single element
            weiter_button = page.locator('button:has-text("Weiter")').first
            # Get the onclick attribute
            onclick = await weiter_button.get_attribute("onclick")
            if onclick:
                # Extract the URL from the onclick attribute
                # Format is typically: window.location.href='URL'
                url = onclick.split("'")[1]
                return url
        except Exception as e:
            logger.error(f"Error getting next page URL: {e}")
            return None
            
        return None 