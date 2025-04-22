# filename: discountcrawlers/spiders/penny_spider.py

import re
import logging
from typing import Iterator, Dict, Any, Optional, List, AsyncIterator
import scrapy
from scrapy.http import Response
from scrapy.exceptions import CloseSpider
from playwright.async_api import Page as PlaywrightPage, TimeoutError as PlaywrightTimeoutError, Locator
from scrapy_playwright.page import PageMethod
from .base import BaseDealsSpider
from discountcrawlers.items import DiscountItem
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class PennySpider(BaseDealsSpider):
    name = "penny"
    allowed_domains = ["penny.at"]
    start_urls = ["https://www.penny.at/angebote"]

    # --- Playwright Settings ---
    custom_settings: Dict[str, Any] = {
        'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'HTTPERROR_ALLOWED_CODES': [403],
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 100_000,
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'PLAYWRIGHT_MAX_CONTEXTS': 1,
    }
    requires_js = True

    # --- Selectors ---
    card_selector: str = "css=li[data-test='product-tile']"

    # Field locators (Keys match DiscountItem fields)
    field_locators: Dict[str, str] = {
        "url": "css=a[data-test='product-tile-link']",
        "name": "css=h3[data-test='product-title']",
        "size": "css=ul[data-test='product-information-piece-description'] li",
        "validity_dates": "css=div[data-test='product-price-validity']",
        "sale_price": "css=div.ws-product-price-type:has(div:text('mit jö Karte')) div.ws-product-price-type__value",
        "original_price": "css=div.ws-product-price-type:has(div:text('ohne jö Karte')) div.ws-product-price-type__value",
        # We'll calculate this from original and sale price
        "discount_percentage": None,
    }

    # Playwright specific selectors
    cookie_accept_selector: str = 'css=button:has-text("Alle Akzeptieren"), button[data-test="accept-all-cookies"]'

    HEADERS: Dict[str, str] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-GB,en;q=0.9,de-AT;q=0.8,de;q=0.7,en-US;q=0.6',
    }

    # --- Request Generation ---
    def start_requests(self) -> Iterator[scrapy.Request]:
        for url in self.start_urls:
            self.logger.info(f"Initiating Playwright request for {url}")
            yield scrapy.Request(
                url=url, headers=self.HEADERS,
                meta={
                    "playwright": True, "playwright_include_page": True,
                    "playwright_page_event_to_wait_for": "networkidle",
                    "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                    "page_num": 1,
                },
                callback=self.parse, errback=self.errback_handle_error, dont_filter=True,
            )

    # --- Parsing Logic ---
    async def parse(self, response: Response) -> AsyncIterator[DiscountItem]:
        page: Optional[PlaywrightPage] = response.meta.get("playwright_page")
        current_page_num = response.meta.get("page_num", 1)

        if not page or page.is_closed():
             self.logger.warning(f"Playwright page object not available or closed for {response.url}. Skipping parse.")
             return

        self.logger.info(f"Parsing page {current_page_num}: {response.url}")

        try:
            await self._handle_popups(page)
            await self._wait_for_cards(page, current_page_num)

            card_locators = await page.locator(self.card_selector).all()
            self.logger.info(f"Page {current_page_num}: Found {len(card_locators)} product card locators.")

            if not card_locators and current_page_num == 1:
                self.logger.error(f"No product card locators found on first page ({response.url}). Check selector or page state.")
                await self._save_screenshot_and_close(page, f"penny_no_locators_page_{current_page_num}.png")
                return

            # --- Item Extraction Loop ---
            items_yielded_count = 0
            for i, card_locator in enumerate(card_locators):
                item = DiscountItem()
                # Use the start_url as base source for now
                item['source_url'] = self.start_urls[0] if self.start_urls else response.url

                try:
                    # Extract data using the defined locators
                    item_data = await self._extract_item_data(card_locator, response)
                    
                    # Update the item with extracted data
                    for field, value in item_data.items():
                        if value is not None:
                            item[field] = value
                    
                    # Calculate discount percentage if not already set
                    if 'discount_percentage' not in item_data and 'original_price' in item_data and 'sale_price' in item_data:
                        original = self._parse_price(item_data['original_price'])
                        sale = self._parse_price(item_data['sale_price'])
                        if original and sale and original > 0:
                            discount_percent = round(((original - sale) / original) * 100)
                            item['discount_percentage'] = f"{discount_percent}%"

                    # Yield item if essential data is present
                    if item.get("url") and item.get("name"):
                        yield item
                        items_yielded_count += 1
                    else:
                        self.logger.debug(f"Skipping item #{i+1} due to missing essential info")

                except Exception as extraction_err:
                    self.logger.error(f"Error extracting data for item #{i+1}: {extraction_err}")
                    continue

            self.logger.info(f"Page {current_page_num}: Yielded {items_yielded_count} items.")

            # --- Pagination Handling ---
            # Look for the pagination next button
            next_button_selector = "css=button:has-text('Weiter')"
            
            # Check if the next button is present and visible
            next_button = page.locator(next_button_selector)
            has_next_button = await next_button.count() > 0
            
            if has_next_button:
                next_page_num = current_page_num + 1
                
                # Get the next page URL from the button's onclick attribute
                next_button_element = next_button.first
                onclick = await next_button_element.get_attribute('onclick')
                
                if onclick:
                    # Extract URL from onclick attribute (format: window.location.href='URL')
                    next_page_url = onclick.split("'")[1]
                    
                    # Convert relative URL to absolute URL if needed
                    if next_page_url.startswith('/'):
                        parsed_url = urlparse(response.url)
                        next_page_url = f"{parsed_url.scheme}://{parsed_url.netloc}{next_page_url}"
                    
                    self.logger.info(f"Found next page button. Proceeding to page {next_page_num}: {next_page_url}")
                    
                    # Create a new request for the next page
                    yield scrapy.Request(
                        url=next_page_url,
                        headers=self.HEADERS,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_event_to_wait_for": "networkidle",
                            "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                            "page_num": next_page_num,
                        },
                        callback=self.parse,
                        errback=self.errback_handle_error,
                        dont_filter=True,
                    )
                else:
                    self.logger.warning("Next page button found but no URL available")
            else:
                self.logger.info(f"No more pages available. Finished at page {current_page_num}")
            
            # Close the current page
            await self._close_page(page)

        except Exception as parse_err:
             self.logger.error(f"General error during parse for page {current_page_num} ({response.url}): {parse_err}")
             await self._save_screenshot_and_close(page, f"penny_parse_error_page_{current_page_num}.png")
             await self._close_page(page)

    # --- Helper Methods ---
    async def _wait_for_cards(self, page: PlaywrightPage, current_page_num: int):
        card_selector_to_wait_for = self.card_selector
        self.logger.info(f"Waiting for product cards using Playwright selector: {card_selector_to_wait_for}")
        try:
            await page.locator(card_selector_to_wait_for).first.wait_for(state='visible', timeout=30000)
            self.logger.info("Product cards are visible via Playwright after waiting.")
            await page.wait_for_timeout(1000)
        except PlaywrightTimeoutError:
            self.logger.error(f"Timeout waiting for product cards on page {current_page_num}. Selector: '{card_selector_to_wait_for}'.")
            raise
        except Exception as wait_err:
            if "closed" in str(wait_err).lower(): 
                self.logger.warning("Page closed during card wait.")
                raise
            else:
                self.logger.error(f"Error waiting for product cards on page {current_page_num}: {wait_err}")
                raise

    async def _extract_item_data(self, card_locator: Locator, response: Response) -> Dict[str, Any]:
        item_data = {}
        
        # Get the list of valid fields
        valid_fields = [
            "url", "name", "size", "validity_dates", "sale_price", 
            "original_price", "discount_percentage", "source_url"
        ]
        
        for field, locator_str in self.field_locators.items():
            # Skip fields that aren't in our valid fields list or don't have a locator
            if field not in valid_fields or not locator_str:
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
                        try:
                            raw_data = await locator.first.text_content(timeout=2000)
                        except Exception:
                            try:
                                raw_data = await locator.first.inner_text(timeout=2000)
                            except Exception:
                                all_texts = await locator.all_text_contents()
                                raw_data = ' '.join(t.strip() for t in all_texts if t.strip()) if all_texts else None

                if raw_data:
                    cleaned_data = self._clean_data(field, raw_data)
                    if cleaned_data is not None:
                        item_data[field] = cleaned_data
            except Exception as e:
                self.logger.debug(f"Could not extract field '{field}' using locator '{locator_str}': {e}")

        # Ensure URL is absolute
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
                self.logger.info("Cookie banner found, attempting to click accept.")
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
            cleaned = cleaned.replace('€', '').replace('*', '').strip()
            cleaned = re.sub(r'(Statt|statt)[:\s]*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'[^\d,.]', '', cleaned).strip()
            if ',' in cleaned:
                cleaned = cleaned.replace(',', '.')
            cleaned = cleaned.strip('.')
        elif field_name == 'validity_dates':
            cleaned = cleaned.replace('\n', ' ')  # Combine potential multiline validity
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        elif field_name == 'size':
            # Improved size extraction
            match = re.search(r'([\d,.]+)\s*(liter|l|kg|g|ml|stück|stk)', cleaned, re.IGNORECASE)
            if match:
                cleaned = f"{match.group(1)} {match.group(2).lower()}"
                
        return cleaned if cleaned else None
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """Parse price string to float"""
        if not price_str:
            return None
        try:
            return float(price_str)
        except ValueError:
            return None
            
    def _get_next_page_url(self, current_url: str, next_page_num: int) -> str:
        """
        Construct the URL for the next page using the ?page= parameter
        """
        # Parse the current URL
        parsed_url = urlparse(current_url)
        
        # Get the existing query parameters
        query_params = parse_qs(parsed_url.query)
        
        # Update or add the page parameter
        query_params['page'] = [str(next_page_num)]
        
        # Reconstruct the query string
        new_query = urlencode(query_params, doseq=True)
        
        # Create a new URL with the updated query parameters
        new_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return new_url

    # --- Error Handling & Closing ---
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
            
        await self._save_screenshot_and_close(page, f"penny_errback_page_{page_num}_{self.name}.png")

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