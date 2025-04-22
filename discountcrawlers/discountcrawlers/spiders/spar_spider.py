# filename: discountcrawlers/spiders/spar_interspar_spider.py

# --- Standard Library Imports ---
import re
import logging
from typing import Iterator, Dict, Any, Optional, List, AsyncIterator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse # For URL manipulation

# --- Scrapy and Related Imports ---
import scrapy
from scrapy.http import Response
from scrapy.exceptions import CloseSpider

# --- Playwright Imports ---
from playwright.async_api import Page as PlaywrightPage, TimeoutError as PlaywrightTimeoutError, Locator

# --- Scrapy-Playwright Imports ---
from scrapy_playwright.page import PageMethod

# --- Project-Specific Imports ---
from .base import BaseDealsSpider
from discountcrawlers.items import DiscountItem


class SparIntersparSpider(BaseDealsSpider):
    name = "spar"
    allowed_domains = ["interspar.at", "www.interspar.at"]
    start_urls = [
        # Using the filtered search URL with page=1 explicitly
        "https://www.interspar.at/shop/lebensmittel/search/?query=*&q=*&hitsPerPage=80&page=1&filter=is-on-promotion:true&substringFilter=pos-visible:8757~~~8958",
        # Alt: "https://www.interspar.at/shop/lebensmittel/search/?filter=is-on-promotion:true&hitsPerPage=80&page=1"
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
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'PLAYWRIGHT_MAX_CONTEXTS': 1,
        # 'LOG_LEVEL': 'DEBUG', # Uncomment for detailed logging
    }
    requires_js = True

    # --- Selectors ---
    card_selector: str = "css=div.productBox[data-url]" # Main product card container

    # Field locators (Relative within card_selector)
    field_locators: Dict[str, str] = {
        "url": "xpath=self::node()", # Special case: get data-url from card itself
        "brand": "css=div.productTitle.mainTitleProd",
        "name": "css=div.productTitle:not(.mainTitleProd)",
        "sale_price_int": "css=label.priceInteger",
        "sale_price_dec": "css=label.priceDecimal",
        "original_price": "css=label.insteadOfPrice",
        "discount_percentage": "css=span.THIS_SELECTOR_DOES_NOT_EXIST",
        "price_per_unit": "css=label.extraInfoPrice",
    }

    # Playwright specific selectors
    # Target the <li> element containing the next link to check for 'disabled' class
    next_page_li_selector: str = 'css=li.next' # !!! VERIFY if this selects the correct <li> !!!
    # Cookie/Onboarding selectors need verification on live site
    cookie_accept_selector: str = 'css=button#onetrust-accept-btn-handler, button:has-text("ALLE AKZEPTIEREN")'
    onboarding_popup_selector: str = 'css=div.onboarding-popup__step-1'
    onboarding_plz_input_selector: str = 'css=input.onboarding-popup__zip-code'
    onboarding_plz_submit_selector: str = 'css=button.onboarding-popup__button-zip:not([disabled])'
    onboarding_delivery_choice_selector: str = 'css=div.onboarding-popup__delivery'
    onboarding_final_submit_selector: str = 'css=button.onboarding-popup__save-pos:not([disabled])'

    # --- Control Parameters ---
    max_pages: int = 20 # Adjust max pages as needed
    ONBOARDING_PLZ: str = "1010" # Example Austrian PLZ

    HEADERS: Dict[str, str] = { # Standard headers
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
                    "playwright_page_event_to_wait_for": "domcontentloaded",
                    "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                    "page_num": 1, # Start page numbering
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
            await self._handle_popups(page)
            await self._wait_for_cards(page, current_page_num)

            card_locators = await page.locator(self.card_selector).all()
            self.logger.info(f"Page {current_page_num}: Found {len(card_locators)} product card locators.")

            # --- Item Extraction Loop ---
            items_yielded_count = 0
            for i, card_locator in enumerate(card_locators):
                # ... (Item extraction using _extract_item_data - same as previous) ...
                item = DiscountItem()
                item['source_url'] = response.url
                try:
                    item_data = await self._extract_item_data(card_locator, response)
                    item.update(item_data)
                    if item.get("url") and (item.get("name") or item.get("sale_price")):
                        yield item
                        items_yielded_count += 1
                except Exception as extraction_err:
                    self.logger.error(f"Error extracting data for item #{i+1} on page {current_page_num}: {extraction_err}")
                    continue

            self.logger.info(f"Page {current_page_num}: Yielded {items_yielded_count} items.")
            if items_yielded_count == 0 and len(card_locators) > 0:
                self.logger.warning(f"Found cards but yielded 0 items on page {current_page_num}. Check locators/cleaning.")


            # --- URL Parameter Pagination Logic ---
            if current_page_num >= self.max_pages:
                self.logger.info(f"Reached max pages limit ({self.max_pages}). Stopping.")
                await self._close_page(page)
                return

            # Check if the 'next' pagination list item is disabled
            next_li = page.locator(self.next_page_li_selector).first
            is_disabled = False
            if await next_li.count() > 0:
                li_class = await next_li.get_attribute("class")
                if li_class and "disabled" in li_class.split():
                    is_disabled = True

            if not is_disabled:
                self.logger.info(f"Next page link found and not disabled on page {current_page_num}.")
                next_page_num = current_page_num + 1

                # Construct next page URL using urllib.parse
                try:
                    parsed_url = urlparse(response.url)
                    query_params = parse_qs(parsed_url.query)
                    query_params['page'] = [str(next_page_num)] # Update page number
                    # Ensure other params like q, filter, etc., are preserved correctly
                    new_query = urlencode(query_params, doseq=True)
                    # Rebuild URL: scheme, netloc, path, params, query, fragment
                    next_page_url = urlunparse((
                        parsed_url.scheme,
                        parsed_url.netloc,
                        parsed_url.path,
                        parsed_url.params,
                        new_query,
                        parsed_url.fragment
                    ))

                    self.logger.info(f"Yielding request for next page: {next_page_url}")
                    # Yield a *new* request for the next page URL
                    yield scrapy.Request(
                        url=next_page_url,
                        headers=self.HEADERS,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_event_to_wait_for": "domcontentloaded",
                            "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                            "page_num": next_page_num, # Pass incremented page number
                        },
                        callback=self.parse,
                        errback=self.errback_handle_error,
                        dont_filter=True,
                    )
                    # We DON'T close the page here, Scrapy handles the Request lifecycle
                except Exception as url_err:
                     self.logger.error(f"Error constructing next page URL from {response.url}: {url_err}")
                     await self._close_page(page) # Close page on URL error

            else:
                self.logger.info(f"Next page link is disabled or not found on page {current_page_num}. Ending pagination.")
                await self._close_page(page) # Close the page when pagination ends

        except Exception as parse_err:
             self.logger.error(f"General error during parse for page {current_page_num} ({response.url}): {parse_err}")
             await self._save_screenshot_and_close(page, f"spar_parse_error_page_{current_page_num}.png")
             await self._close_page(page)

    # --- Helper Methods ---
    # _wait_for_cards, _extract_item_data, _handle_popups, _clean_data,
    # errback_handle_error, _close_page, _save_screenshot_and_close
    # Implementations remain the same as the previous full code example.
    # Make sure to include them here.
    # --- (Include the full implementations of these methods here) ---
    async def _wait_for_cards(self, page: PlaywrightPage, current_page_num: int):
        # ... (Implementation from previous response) ...
        card_selector_to_wait_for = self.card_selector
        self.logger.info(f"Waiting for product cards using Playwright selector: {card_selector_to_wait_for}")
        try:
            await page.locator(card_selector_to_wait_for).first.wait_for(state='visible', timeout=25000)
            self.logger.info("Product cards are visible via Playwright after waiting.")
            await page.wait_for_timeout(1000)
        except PlaywrightTimeoutError:
            self.logger.error(f"Timeout waiting for product cards on page {current_page_num}. Selector: '{card_selector_to_wait_for}'.")
            raise
        except Exception as wait_err:
            if "closed" in str(wait_err).lower(): self.logger.warning("Page closed during card wait."); raise
            else: self.logger.error(f"Error waiting for product cards on page {current_page_num}: {wait_err}"); raise

    async def _extract_item_data(self, card_locator: Locator, response: Response) -> Dict[str, Any]:
        # ... (Implementation from previous response) ...
        item_data = {}; raw_values = {}
        url_locator = self.field_locators.get("url")
        if url_locator == "xpath=self::node()":
             raw_url = await card_locator.get_attribute('data-url', timeout=2000)
             raw_values["url"] = raw_url
             if raw_url: item_data["url"] = response.urljoin(raw_url.strip())
        for field, locator_str in self.field_locators.items():
            if field == "url" or field not in DiscountItem.fields or field in ["sale_price_int", "sale_price_dec"]: continue
            raw_data: Optional[str] = None
            try:
                if locator_str.startswith("xpath="): element_locator = card_locator.locator(locator_str)
                elif locator_str.startswith("css="): element_locator = card_locator.locator(locator_str.replace("css=","", 1))
                else: element_locator = card_locator.locator(locator_str)
                if await element_locator.count() > 0:
                    try: raw_data = await element_locator.first.text_content(timeout=2000)
                    except Exception: raw_data = await element_locator.first.inner_text(timeout=2000)
                raw_values[field] = raw_data
                if raw_data:
                    cleaned_data = self._clean_data(field, raw_data)
                    if cleaned_data is not None: item_data[field] = cleaned_data
            except Exception as e: self.logger.debug(f"Could not extract field '{field}' using locator '{locator_str}': {e}")
        price_int_raw = await self._safe_get_text(card_locator, self.field_locators.get("sale_price_int", ""))
        price_dec_raw = await self._safe_get_text(card_locator, self.field_locators.get("sale_price_dec", ""))
        raw_values["sale_price_int"] = price_int_raw; raw_values["sale_price_dec"] = price_dec_raw
        if price_int_raw and price_dec_raw:
             combined_price_str = f"{price_int_raw.strip()},{price_dec_raw.strip()}"
             cleaned_price = self._clean_data("sale_price", combined_price_str)
             if cleaned_price is not None: item_data["sale_price"] = cleaned_price
        elif price_int_raw:
             cleaned_price = self._clean_data("sale_price", price_int_raw)
             if cleaned_price is not None: item_data["sale_price"] = cleaned_price
        return item_data

    async def _safe_get_text(self, parent_locator: Locator, selector: str) -> Optional[str]:
         """Safely gets text content from a locator relative to a parent."""
         if not selector: return None
         try:
             if selector.startswith("xpath="): element_locator = parent_locator.locator(selector)
             elif selector.startswith("css="): element_locator = parent_locator.locator(selector.replace("css=","", 1))
             else: element_locator = parent_locator.locator(selector)

             if await element_locator.count() > 0:
                  return await element_locator.first.text_content(timeout=1500) # Shorter timeout for parts
         except Exception:
              pass # Ignore errors getting optional parts like price decimals
         return None


    async def _handle_popups(self, page: PlaywrightPage):
        # (Implementation from previous response)
        if page.is_closed(): return
        self.logger.debug("Checking for onboarding/cookie popups...")
        # Onboarding Check
        try:
            onboarding_popup = page.locator(self.onboarding_popup_selector).first
            if await onboarding_popup.is_visible(timeout=10000):
                self.logger.info("Onboarding popup (PLZ step) detected.")
                plz_input = page.locator(self.onboarding_plz_input_selector).first
                plz_submit = page.locator(self.onboarding_plz_submit_selector).first
                await plz_input.fill(self.ONBOARDING_PLZ)
                self.logger.info(f"Filled PLZ: {self.ONBOARDING_PLZ}")
                await page.wait_for_timeout(500)
                await plz_submit.wait_for(state="visible", timeout=5000); await plz_submit.wait_for(state="enabled", timeout=5000)
                await plz_submit.click(timeout=5000)
                self.logger.info("Clicked PLZ submit ('Weiter').")
                await page.wait_for_timeout(1000)
                delivery_choice = page.locator(self.onboarding_delivery_choice_selector).first
                await delivery_choice.wait_for(state="visible", timeout=10000); await delivery_choice.click(timeout=5000)
                self.logger.info("Selected home delivery option.")
                await page.wait_for_timeout(500)
                final_submit = page.locator(self.onboarding_final_submit_selector).first
                await final_submit.wait_for(state="visible", timeout=5000); await final_submit.wait_for(state="enabled", timeout=5000)
                await final_submit.click(timeout=5000)
                self.logger.info("Clicked final onboarding submit ('Einkauf starten').")
                await page.wait_for_timeout(2000)
            else: self.logger.debug("Onboarding popup not detected.")
        except Exception as e:
             if "closed" in str(e).lower(): return
             self.logger.warning(f"Error or timeout during onboarding handling: {e}")
        # Cookie Consent Check
        if page.is_closed(): return
        try:
            cookie_button = page.locator(self.cookie_accept_selector).first
            if await cookie_button.is_visible(timeout=7000):
                self.logger.info("Cookie banner found, attempting to click accept.")
                await cookie_button.click(timeout=5000, force=True)
                await page.wait_for_timeout(1500); self.logger.info("Cookie banner likely accepted.")
            else: self.logger.debug("Cookie banner not visible.")
        except Exception as e:
            if "closed" in str(e).lower(): return
            self.logger.warning(f"Could not click cookie button: {e}")
        self.logger.debug("Finished checking popups.")

    def _clean_data(self, field_name: str, raw_data: str) -> Optional[str]:
        # (Implementation from previous response)
        if not raw_data: return None
        cleaned = raw_data.replace('\xa0', ' ').strip(); cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned: return None
        if field_name in ['sale_price', 'original_price']:
            cleaned = re.sub(r'(Statt|statt|Nur|nur)[:\s]*', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.replace('€', '').replace('*', '').strip(); cleaned = re.sub(r'^\s*-\s*', '', cleaned)
            if ' - ' in cleaned: cleaned = cleaned.split(' - ')[0].strip()
            cleaned = re.sub(r'\s*/\s*.*$', '', cleaned).strip()
            cleaned = re.sub(r'[^\d,.-]', '', cleaned).strip()
            if ',' in cleaned and '.' in cleaned:
                 if cleaned.rfind('.') > cleaned.rfind(','): cleaned = cleaned.replace(',', '')
                 else: cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned: cleaned = cleaned.replace(',', '.')
            if cleaned == '-': return None
        elif field_name == 'discount_percentage': cleaned = re.sub(r'[^\d]', '', cleaned).strip()
        elif field_name == 'price_per_unit':
             cleaned = cleaned.replace('€', '').strip()
             match = re.search(r'\((.*?)\)', cleaned);
             if match: cleaned = match.group(1).strip()
        return cleaned if cleaned else None

    async def errback_handle_error(self, failure):
        # (Standard implementation from verified XXXLutz version)
        request = failure.request; request_url = request.url
        page: Optional[PlaywrightPage] = request.meta.get("playwright_page")
        page_num = request.meta.get("page_num", "unknown")
        self.logger.error(f"Request failed for URL: {request_url} (Page Attempted: {page_num})")
        self.logger.error(f"Failure type: {failure.type}, Value: {failure.value}")
        if page and page.is_closed(): self.logger.warning(f"Page for {request_url} was already closed when errback called."); return
        response = getattr(failure.value, 'response', None)
        if response: self.logger.error(f"Received status {response.status} for {request_url}")
        await self._save_screenshot_and_close(page, f"spar_errback_page_{page_num}_{self.name}.png")

    async def _close_page(self, page: Optional[PlaywrightPage]):
        # (Standard implementation from verified XXXLutz version)
        if page and not page.is_closed():
            page_url = "unknown URL";
            try: page_url = page.url
            except Exception: pass
            try: await page.context.close(); self.logger.info(f"Playwright context closed for page related to: {page_url}")
            except Exception as close_err: self.logger.error(f"Error closing Playwright page/context ({page_url}): {close_err}")

    async def _save_screenshot_and_close(self, page: Optional[PlaywrightPage], filename="error_screenshot.png"):
        # (Standard implementation from verified XXXLutz version)
        if page and not page.is_closed():
            page_url = "unknown URL";
            try: page_url = page.url; await page.screenshot(path=filename, full_page=True); self.logger.info(f"Screenshot saved to {filename} for URL: {page_url}")
            except Exception as img_err: self.logger.error(f"Failed to save screenshot to {filename} for URL {page_url}: {img_err}")
            await self._close_page(page)