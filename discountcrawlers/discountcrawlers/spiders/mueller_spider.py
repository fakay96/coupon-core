# filename: discountcrawlers/spiders/mueller_spider.py

# --- Standard Library Imports ---
import re
import logging
from typing import Iterator, Dict, Any, Optional, List, AsyncIterator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# --- Scrapy and Related Imports ---
import scrapy
from scrapy.http import Response
from scrapy.exceptions import CloseSpider

# --- Playwright Imports ---
from playwright.async_api import Page as PlaywrightPage, TimeoutError as PlaywrightTimeoutError, Locator

# --- Scrapy-Playwright Imports ---
from scrapy_playwright.page import PageMethod

# --- Project-Specific Imports ---
from .base import BaseDealsSpider # Assuming BaseDealsSpider exists
# Import the MODIFIED DiscountItem
from discountcrawlers.items import DiscountItem


class MuellerSpider(BaseDealsSpider):
    """
    Spider for Müller promotions using Playwright for dynamic content and pagination.
    """
    name = "mueller"
    allowed_domains = ["www.mueller.at"]
    start_urls = [
        # Add page=1 to start URLs
        "https://www.mueller.at/c/parfuemerie/aktionen/?page=1",
        "https://www.mueller.at/c/drogerie/aktionen/?page=1",
    ]

    # --- Playwright Settings ---
    custom_settings: Dict[str, Any] = {
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'HTTPERROR_ALLOWED_CODES': [403],
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 100_000,
        'CONCURRENT_REQUESTS': 1, # Keep low for stability
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'PLAYWRIGHT_MAX_CONTEXTS': 1,
        # 'LOG_LEVEL': 'DEBUG',
    }
    requires_js = True

    # --- Selectors (Updated based on provided HTML) ---
    # Using the outer div specific to the list context
    card_selector: str = "css=div.product-list_component_product-list__tile__C5Lji"

    # Field locators (Relative CSS within card_selector)
    field_locators: Dict[str, str] = {
        # Target the main link for the item
        "url": "css=a[href^='/p/']",
        "name": "css=div.product-tile_component_product-tile__product-name__xG25c",
        "sale_price": "css=span.product-price_component_product-price__main-price-accent__zHz13",
        "original_price": "css=span.product-price_component_product-price__strike-price-value__vR1hW",
        "discount_percentage": "css=span.THIS_SELECTOR_DOES_NOT_EXIST", # Not found
        "price_per_unit": "css=span.product-price_component_product-price__base-price__HFAt_",
        "size": "css=span.product-price_component_product-price__capacity__9H0TW",
        "stock_info": "css=div.product-tile_component_product-tile__label-text__vPARR", # e.g., "ausverkauft"
        # "brand": "css=...", # Add if identifiable
    }

    # Playwright specific selectors
    next_page_link_selector: str = 'css=a[aria-label="Nächste Seite"], a[rel="next"]' 
    cookie_accept_selector: str = 'css=button:has-text("Alle zulassen"), button#onetrust-accept-btn-handler'

    # --- Control Parameters ---
    max_pages: int = 20 # From original stub, adjust if needed

    HEADERS: Dict[str, str] = { # Standard headers
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-GB,en;q=0.9,de-AT;q=0.8,de;q=0.7,en-US;q=0.6',
    }

    # --- Request Generation ---
    def start_requests(self) -> Iterator[scrapy.Request]:
        for url in self.start_urls:
            self.logger.info(f"Initiating Playwright request for {url}")
            # Extract initial page number from URL, default to 1
            page_num = 1
            try:
                query_params = parse_qs(urlparse(url).query)
                page_num = int(query_params.get('page', [1])[0])
            except Exception:
                self.logger.warning(f"Could not parse page number from start URL: {url}. Assuming page 1.")

            yield scrapy.Request(
                url=url, headers=self.HEADERS,
                meta={
                    "playwright": True, "playwright_include_page": True,
                    "playwright_page_event_to_wait_for": "domcontentloaded",
                    "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                    "page_num": page_num, # Pass initial page number
                },
                callback=self.parse, errback=self.errback_handle_error, dont_filter=True,
            )

    # --- Parsing Logic ---
    async def parse(self, response: Response) -> AsyncIterator[DiscountItem]:
        page: Optional[PlaywrightPage] = response.meta.get("playwright_page")
        current_page_num = response.meta.get("page_num", 1)

        if not page or page.is_closed():
            self.logger.warning(f"Playwright page object not available or closed for {response.url} (Page {current_page_num}). Skipping parse.")
            return

        self.logger.info(f"Parsing page {current_page_num}: {response.url}")

        try:
            await self._handle_popups(page) # Handle cookies
            await self._wait_for_cards(page, current_page_num) # Wait for cards

            card_locators = await page.locator(self.card_selector).all()
            self.logger.info(f"Page {current_page_num}: Found {len(card_locators)} product card locators.")

            if not card_locators and current_page_num == 1:
                self.logger.error(f"No product card locators found on first page ({response.url}). Check selector '{self.card_selector}' or page state.")
                # Don't return immediately, check pagination first

            # --- Item Extraction Loop ---
            items_yielded_count = 0
            for i, card_locator in enumerate(card_locators):
                item = DiscountItem()
                item['source_url'] = response.url # URL where item was found

                try:
                    # Extract data using helper function
                    item_data = await self._extract_item_data(card_locator, response)
                    # Update the item directly (field names match DiscountItem)
                    item.update(item_data)

                    # Yield item if essential data is present
                    if item.get("url") and item.get("name"):
                        yield item
                        items_yielded_count += 1
                    else:
                        self.logger.debug(f"Skipping item #{i+1} due to missing info: {item}")

                except Exception as extraction_err:
                    self.logger.error(f"Error extracting data for item #{i+1} on page {current_page_num}: {extraction_err}")
                    continue

            self.logger.info(f"Page {current_page_num}: Yielded {items_yielded_count} items.")

            # --- Pagination Logic - FIXED ---
            if current_page_num >= self.max_pages:
                self.logger.info(f"Reached max pages limit ({self.max_pages}). Stopping.")
                await self._close_page(page)
                return

            # Check if a 'next' page link exists and is valid
            next_page_exists = await page.locator(self.next_page_link_selector).count() > 0
            if next_page_exists:
                next_page_locator = page.locator(self.next_page_link_selector).first
                
                # Check if the next page link is visible
                is_visible = False
                try:
                    is_visible = await next_page_locator.is_visible(timeout=5000)
                except Exception as e:
                    self.logger.warning(f"Error checking next page visibility: {e}")
                
                if is_visible:
                    href = await next_page_locator.get_attribute("href")
                    if href and href != '#':
                        next_page_url = response.urljoin(href) # Construct absolute URL
                        
                        # Determine next page number
                        next_page_num = current_page_num + 1
                        try:
                            parsed_url = urlparse(next_page_url)
                            query_params = parse_qs(parsed_url.query)
                            if 'page' in query_params and query_params['page']:
                                next_page_num = int(query_params['page'][0])
                        except Exception as e:
                            self.logger.warning(f"Could not parse page number from URL {next_page_url}: {e}")
                        
                        self.logger.info(f"Found next page link: {next_page_url} (Page {next_page_num})")
                        
                        yield scrapy.Request(
                            url=next_page_url,
                            headers=self.HEADERS,
                            meta={
                                "playwright": True, 
                                "playwright_include_page": True,
                                "playwright_page_event_to_wait_for": "domcontentloaded",
                                "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                                "page_num": next_page_num,
                            },
                            callback=self.parse,
                            errback=self.errback_handle_error,
                            dont_filter=True,
                        )
                    else:
                        self.logger.info("Next page link found but has no valid href.")
                        await self._close_page(page)
                else:
                    self.logger.info("Next page link found but is not visible.")
                    await self._close_page(page)
            else:
                self.logger.info(f"No next page link found using selector '{self.next_page_link_selector}'. Ending pagination.")
                await self._close_page(page)

        except Exception as parse_err:
            self.logger.error(f"General error during parse for page {current_page_num} ({response.url}): {parse_err}")
            await self._save_screenshot_and_close(page, f"mueller_parse_error_page_{current_page_num}.png")
            await self._close_page(page)

    # --- Helper Methods (Fully implemented) ---
    async def _wait_for_cards(self, page: PlaywrightPage, current_page_num: int):
        card_selector_to_wait_for = self.card_selector
        self.logger.info(f"Waiting for product cards using selector: {card_selector_to_wait_for}")
        try:
            await page.locator(card_selector_to_wait_for).first.wait_for(state='visible', timeout=30000)
            self.logger.info("Product cards visible after waiting.")
            await page.wait_for_timeout(1000)
        except PlaywrightTimeoutError:
            self.logger.error(f"Timeout waiting for cards on page {current_page_num}. Selector: '{card_selector_to_wait_for}'.")
            raise
        except Exception as wait_err:
            if "closed" in str(wait_err).lower():
                self.logger.warning("Page closed during card wait.")
                raise
            else:
                self.logger.error(f"Error waiting for cards page {current_page_num}: {wait_err}")
                raise

    async def _extract_item_data(self, card_locator: Locator, response: Response) -> Dict[str, Any]:
        item_data = {}
        for field, locator_str in self.field_locators.items():
            if field not in DiscountItem.fields:
                if "THIS_SELECTOR_DOES_NOT_EXIST" not in locator_str:
                    self.logger.debug(f"Skipping locator for undefined field '{field}'.")
                continue
                
            raw_data: Optional[str] = None
            try:
                if locator_str.startswith("xpath="):
                    locator = card_locator.locator(locator_str)
                elif locator_str.startswith("css="):
                    locator = card_locator.locator(locator_str.replace("css=", "", 1))
                else:
                    locator = card_locator.locator(locator_str)

                if await locator.count() > 0:
                    if field == "url":
                        raw_data = await locator.first.get_attribute('href', timeout=2000)
                    else:
                        all_texts = await locator.first.all_text_contents()
                        raw_data = ' '.join(t.strip() for t in all_texts if t.strip()) if all_texts else None
                        if not raw_data:  # Fallback
                            try:
                                raw_data = await locator.first.text_content(timeout=2000)
                            except Exception:
                                raw_data = await locator.first.inner_text(timeout=2000)
                                
                if raw_data:
                    cleaned_data = self._clean_data(field, raw_data)
                    if cleaned_data is not None:
                        item_data[field] = cleaned_data
                        
            except Exception as e:
                if "THIS_SELECTOR_DOES_NOT_EXIST" not in locator_str:
                    self.logger.debug(f"Could not extract field '{field}': {e}")
                    
        if "url" in item_data and item_data["url"]:
            item_data["url"] = response.urljoin(item_data["url"])
            
        return item_data

    async def _handle_popups(self, page: PlaywrightPage):
        if page.is_closed():
            return
            
        self.logger.debug("Checking for cookie popups...")
        try:
            cookie_button = page.locator(self.cookie_accept_selector).first
            if await cookie_button.is_visible(timeout=15000):
                self.logger.info("Cookie banner found, clicking accept.")
                await cookie_button.click(timeout=5000, force=True)
                await page.wait_for_timeout(1500)
                self.logger.info("Cookie banner likely accepted.")
            else:
                self.logger.debug("Cookie banner not visible.")
        except Exception as e:
            if "closed" in str(e).lower():
                return
            self.logger.warning(f"Could not click cookie button: {e}")
        self.logger.debug("Finished checking popups.")

    def _clean_data(self, field_name: str, raw_data: str) -> Optional[str]:
        if not raw_data:
            return None
            
        cleaned = raw_data.replace('\xa0', ' ').strip()
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if not cleaned:
            return None
            
        if field_name in ['sale_price', 'original_price']:
            cleaned = cleaned.replace('€', '').strip()
            # Handle potential thousand separators (like '.') before the comma decimal
            if '.' in cleaned and ',' in cleaned and cleaned.rfind('.') < cleaned.rfind(','):
                cleaned = cleaned.replace('.', '')
            cleaned = cleaned.replace(',', '.')  # Standardize decimal point
            cleaned = re.sub(r'[^\d.]', '', cleaned).strip('.')  # Keep only digits and decimal point
        elif field_name == 'price_per_unit':
            cleaned = cleaned.replace('€', '').strip()
            # Extract value and unit, e.g., "113.33 / 1 l"
            cleaned = re.sub(r'\s*/\s*', '/', cleaned)  # Standardize separator
        elif field_name == 'size':
            cleaned = cleaned.replace('/', '').strip()  # Remove leading slash
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()  # Normalize space

        return cleaned if cleaned else None

    async def errback_handle_error(self, failure):
        request = failure.request
        request_url = request.url
        page: Optional[PlaywrightPage] = request.meta.get("playwright_page")
        page_num = request.meta.get("page_num", "unknown")
        
        self.logger.error(f"Request failed for URL: {request_url} (Page: {page_num})")
        self.logger.error(f"Failure type: {failure.type}, Value: {failure.value}")
        
        if page and page.is_closed():
            self.logger.warning(f"Page for {request_url} already closed.")
            return
            
        response = getattr(failure.value, 'response', None)
        if response:
            self.logger.error(f"Received status {response.status} for {request_url}")
            
        await self._save_screenshot_and_close(page, f"mueller_errback_page_{page_num}_{self.name}.png")

    async def _close_page(self, page: Optional[PlaywrightPage]):
        if page and not page.is_closed():
            page_url = "unknown"
            try:
                page_url = page.url
            except Exception:
                pass
                
            try:
                await page.context.close()
                self.logger.info(f"Playwright context closed for page: {page_url}")
            except Exception as close_err:
                self.logger.error(f"Error closing Playwright context ({page_url}): {close_err}")

    async def _save_screenshot_and_close(self, page: Optional[PlaywrightPage], filename="error_screenshot.png"):
        if page and not page.is_closed():
            page_url = "unknown"
            try:
                page_url = page.url
            except Exception:
                pass
                
            try:
                await page.screenshot(path=filename, full_page=True)
                self.logger.info(f"Screenshot saved: {filename} (URL: {page_url})")
            except Exception as img_err:
                self.logger.error(f"Failed to save screenshot {filename} (URL: {page_url}): {img_err}")
                
            await self._close_page(page)