"""
Generic base spider for deal scraping.

Defines BaseDealsSpider with pagination and extraction logic.
"""

from __future__ import annotations
import re
from typing import Iterator, Any, Dict, Optional
import scrapy
from scrapy import Request, Spider
from scrapy.http import Response
from scrapy.exceptions import CloseSpider
from discountcrawlers.items import DiscountItem
import logging

LOGGER = logging.getLogger(__name__)

class BaseDiscountSpider(Spider):
    """Base spider class for all discount crawlers."""
    
    name: str = "base_discount_spider"
    allowed_domains: list = []
    start_urls: list = []
    
    # Custom settings
    custom_settings: Dict[str, Any] = {
       
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def start_requests(self):
        """Start requests for the spider."""
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse)
    
    def parse(self, response: Response, **kwargs) -> Optional[Dict[str, Any]]:
        """Parse the response and yield items or requests."""
        raise NotImplementedError("Subclasses must implement parse method")
    
    def parse_discount(self, response: Response, **kwargs) -> DiscountItem:
        """Parse a discount item from the response."""
        raise NotImplementedError("Subclasses must implement parse_discount method")
    
    def handle_error(self, failure):
        """Handle request failures."""
        self.logger.error(f"Request failed: {failure.value}")
        return None
    
    def closed(self, reason):
        """Called when the spider is closed."""
        self.logger.info(f"Spider closed: {reason}")
    
    def _validate_response(self, response: Response) -> bool:
        """Validate the response before processing."""
        if response.status != 200:
            self.logger.error(f"Invalid response status: {response.status}")
            return False
        return True
    
    def _extract_price(self, selector: str, response: Response) -> Optional[float]:
        """Extract and clean price from selector."""
        try:
            price_text = response.css(selector).get()
            if not price_text:
                return None
            # Remove currency symbols and commas, convert to float
            price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
            return price
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error extracting price: {e}")
            return None
    
    def _calculate_discount_percentage(self, original_price: float, current_price: float) -> Optional[float]:
        """Calculate discount percentage."""
        try:
            if not original_price or not current_price:
                return None
            return ((original_price - current_price) / original_price) * 100
        except (ValueError, TypeError, ZeroDivisionError) as e:
            self.logger.error(f"Error calculating discount: {e}")
            return None

class BaseDealsSpider(scrapy.Spider):
    """Generic deals spider with pagination support."""
    pagination_type: str = "none"
    page_param: str = "p"
    max_pages: int = 5
    card_selector: str
    field_selectors: dict[str, str]

    def start_requests(self) -> Iterator[Request]:
        """Generate initial requests, with Playwright meta for infinite scroll."""
        for url in self.start_urls:
            meta = {"page": 1}
            if self.pagination_type == "infinite_scroll":
                from scrapy_playwright.page import PageMethod
                meta.update({
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_timeout": 60000,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("evaluate", "window.scrollTo(0, document.body.scrollHeight)"),
                        PageMethod("wait_for_timeout", 2000),
                    ],
                })
            yield Request(url=url, callback=self.parse, meta=meta, dont_filter=True)

    def parse(self, response: Response) -> Iterator[DiscountItem]:
        """Parse items and handle pagination."""
        cards = response.css(self.card_selector)
        for card in cards:
            item = DiscountItem()
            for field, sel in self.field_selectors.items():
                item[field] = card.css(sel).get(default="").strip()
            yield item

        if self.pagination_type == "page_param":
            current = response.meta.get("page", 1)
            if current < self.max_pages and cards:
                next_page = current + 1
                if "?" in response.url:
                    url = re.sub(
                        rf"([?&]){self.page_param}=\d+",
                        rf"\1{self.page_param}={next_page}",
                        response.url,
                    )
                    if url == response.url:
                        url += f"&{self.page_param}={next_page}"
                else:
                    url = f"{response.url}?{self.page_param}={next_page}"
                meta = dict(response.meta, page=next_page)
                yield Request(url=url, callback=self.parse, meta=meta, dont_filter=True)