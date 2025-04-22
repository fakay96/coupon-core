"""
Spider for scraping Zalando Austria outlet pages using Scrapy and Playwright.
Extracts product details from dynamically rendered pages, handles pagination,
and captures errors via screenshots.
"""
import re
from typing import AsyncIterator, ClassVar, Dict, Optional, Any

import scrapy
from scrapy.http import Response
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod
from playwright.async_api import Page as PlaywrightPage, TimeoutError as PlaywrightTimeoutError

from .base import BaseDealsSpider
from discountcrawlers.items import DiscountItem


class ZalandoSpider(BaseDealsSpider):
    """
    Spider for scraping Zalando Austria outlet pages for women's products.

    Uses Playwright to render JavaScript, extract product details,
    and navigate through pagination up to a specified maximum.
    """
    name: ClassVar[str] = "zalando"
    allowed_domains: ClassVar[list[str]] = ["www.zalando.at"]
    start_urls: ClassVar[list[str]] = ["https://www.zalando.at/outlet-damen/"]

    # --- Playwright Settings ---
    custom_settings: ClassVar[Dict[str, Any]] = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "HTTPERROR_ALLOWED_CODES": [403],
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "PLAYWRIGHT_MAX_CONTEXTS": 1,
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }
    requires_js: ClassVar[bool] = True

    # --- Selectors ---
    card_selector: ClassVar[str] = 'article.z5x6ht'
    field_selectors: ClassVar[Dict[str, str]] = {
        "url": "a::attr(href)",
        "brand": "h3.OBkCPz::text",
        "name": "header h3.voFjEy::text",
        "sale_price": "section p:first-of-type span.Km7l2y::text",
        "original_price": "span.ZiDB59::text",
        "discount_percentage": "section p span.Km7l2y:last-of-type::text",
    }
    next_page_selector: ClassVar[str] = (
        'a[aria-label="next page"], a[data-testid="pagination-next"]'
    )
    cookie_accept_selector: ClassVar[str] = (
        'button#onetrust-accept-btn-handler, button:has-text("Alle Cookies akzeptieren")'
    )

    MAX_PAGES: ClassVar[int] = 50

    HEADERS: ClassVar[Dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9," 
            "image/avif,image/webp,image/apng,*/*;q=0.8," 
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language": "en-GB,en;q=0.9,de-AT;q=0.8,de;q=0.7,en-US;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-CH-UA": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    def start_requests(self) -> scrapy.Request:
        """
        Yield initial Playwright-enabled requests for the outlet page.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                headers=self.HEADERS,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_event_to_wait_for": "networkidle",
                    "playwright_navigation_timeout": 30000,
                    "playwright_context_kwargs": {
                        "extra_http_headers": self.HEADERS,
                        "viewport": {"width": 1920, "height": 1080},
                    },
                    "current_page": 1,
                },
                callback=self.parse,
                errback=self.errback_handle_error,
                dont_filter=True,
            )

    async def parse(self, response: Response) -> AsyncIterator[DiscountItem]:
        """
        Parse rendered page, extract product items, and follow pagination.
        """
        page: Optional[PlaywrightPage] = response.meta.get("playwright_page")
        current_page: int = response.meta.get("current_page", 1)

        if not page or page.is_closed():
            self.logger.error(f"Playwright page unavailable for {response.url}")
            return

        try:
            # Handle cookie consent
            await self._handle_popups(page)
            
            # Wait for product cards
            await self._wait_for_cards(page)
            
            # Get all product cards
            cards = response.css(self.card_selector)
            self.logger.info(f"Found {len(cards)} product cards on page {current_page}")

            if not cards and current_page == 1:
                self.logger.error(f"No product cards found on first page. URL: {response.url}")
                await self._save_screenshot_and_close(page, f"zalando_no_cards_page_{current_page}.png")
                return

            # Process each product card
            for card in cards:
                try:
                    item = DiscountItem()
                    item["source_url"] = response.url
                    
                    # Extract data from card
                    for field, selector in self.field_selectors.items():
                        raw = card.css(selector).get()
                        item[field] = self._clean(raw) if raw else None

                    if url := item.get("url"):
                        item["url"] = response.urljoin(url.strip())

                    if item.get("url") and (item.get("brand") or item.get("name")):
                        yield item
                except Exception as e:
                    self.logger.error(f"Error processing card: {e}")
                    continue

            # Handle pagination
            if current_page < self.MAX_PAGES:
                next_btn = page.locator(self.next_page_selector).first
                if await next_btn.count() and await next_btn.is_enabled(timeout=5000):
                    await next_btn.click(timeout=15000)
                    await page.wait_for_selector(self.card_selector, state="visible", timeout=30000)
                    
                    yield scrapy.Request(
                        url=page.url,
                        headers=self.HEADERS,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_event_to_wait_for": "networkidle",
                            "playwright_navigation_timeout": 30000,
                            "playwright_context_kwargs": {
                                "extra_http_headers": self.HEADERS,
                                "viewport": {"width": 1920, "height": 1080},
                            },
                            "current_page": current_page + 1,
                        },
                        callback=self.parse,
                        errback=self.errback_handle_error,
                        dont_filter=True,
                    )

        except Exception as e:
            self.logger.error(f"Error parsing page {current_page}: {e}")
            await self._save_screenshot_and_close(page, f"zalando_error_page_{current_page}.png")
        finally:
            await self._close_page(page)

    async def _wait_for_cards(self, page: PlaywrightPage):
        """Wait for product cards to be visible."""
        try:
            await page.locator(self.card_selector).first.wait_for(
                state='visible',
                timeout=30000
            )
            await page.wait_for_timeout(2000)  # Additional wait for dynamic content
        except PlaywrightTimeoutError:
            self.logger.error("Timeout waiting for product cards")
            raise
        except Exception as e:
            self.logger.error(f"Error waiting for cards: {e}")
            raise

    async def _handle_popups(self, page: PlaywrightPage):
        """Handle cookie consent and other popups."""
        try:
            cookie_button = page.locator(self.cookie_accept_selector).first
            if await cookie_button.is_visible(timeout=5000):
                await cookie_button.click(timeout=5000)
                await page.wait_for_timeout(1000)
        except Exception as e:
            self.logger.debug(f"Error handling popups: {e}")

    def _clean(self, raw: str) -> Optional[str]:
        """
        Clean raw text by stripping and removing currency/percentage symbols.
        """
        if not raw:
            return None
            
        text = raw.replace("€", "").replace("%", "").strip()
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return None
            
        # Handle price formatting
        if '.' in text and ',' in text and text.rfind('.') < text.rfind(','):
            text = text.replace('.', '')
        text = text.replace(',', '.')
        text = re.sub(r'[^\d.]', '', text).strip('.')
        
        return text if text else None

    async def _save_screenshot_and_close(self, page: Optional[PlaywrightPage], filename: str):
        """Save a screenshot and close the page."""
        if page and not page.is_closed():
            try:
                await page.screenshot(path=filename, full_page=True)
                self.logger.info(f"Screenshot saved: {filename}")
            except Exception as e:
                self.logger.error(f"Error saving screenshot: {e}")
            await this._close_page(page)

    async def _close_page(self, page: Optional[PlaywrightPage]):
        """Close the Playwright page and context."""
        if page and not page.is_closed():
            try:
                await page.context.close()
            except Exception as e:
                self.logger.error(f"Error closing page: {e}")

    async def errback_handle_error(self, failure):
        """Handle request errors."""
        request = failure.request
        page: Optional[PlaywrightPage] = request.meta.get("playwright_page")
        page_num = request.meta.get("current_page", "unknown")
        
        self.logger.error(f"Request failed for URL: {request.url} (Page: {page_num})")
        self.logger.error(f"Failure: {failure.value}")
        
        if page and not page.is_closed():
            await this._save_screenshot_and_close(page, f"zalando_errback_page_{page_num}.png")