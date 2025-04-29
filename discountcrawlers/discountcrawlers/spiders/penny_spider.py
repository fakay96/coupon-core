# filename: discountcrawlers/spiders/penny_spider.py
import re
import logging
from typing import Iterator, Dict, Any, Optional, List, AsyncIterator

import scrapy
from scrapy.http import Response
from scrapy.exceptions import CloseSpider
from playwright.async_api import (
    Page as PlaywrightPage,
    TimeoutError as PlaywrightTimeoutError,
    Locator,
)
from scrapy_playwright.page import PageMethod

from .base import BaseDealsSpider
from discountcrawlers.items import DiscountItem
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class PennySpider(BaseDealsSpider):
    name = "penny"
    allowed_domains = ["penny.at"]
    start_urls = ["https://www.penny.at/angebote"]

    # --- Playwright Settings -------------------------------------------------
    custom_settings: Dict[str, Any] = {
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "HTTPERROR_ALLOWED_CODES": [403],
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 100_000,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "PLAYWRIGHT_MAX_CONTEXTS": 1,
    }
    requires_js = True

    # --- Selectors -----------------------------------------------------------
    card_selector: str = "css=li[data-test='product-tile']"

    # Field locators (keys map to DiscountItem fields)
    # ------------------------------------------------------------------------
    field_locators: Dict[str, str] = {
        "url": "css=a[data-test='product-tile-link']",
        "name": "css=h3[data-test='product-title']",
        "size": "css=ul[data-test='product-information-piece-description'] li",
        "validity_dates": "css=div[data-test='product-price-validity']",

        
        "sale_price": (
            "css=div[data-test='product-price'] strong, "
            "css=div[data-test='product-price'] span.price-current"
        ),
        "original_price": (
            "css=div[data-test='product-price'] del, "
            "css=div[data-test='product-price'] span.price-old"
        ),
        "price": (
            "css=div[data-test='product-price'] del, "
            "css=div[data-test='product-price'] span.price-old"
        ),
        # Calculated later from the two prices
        "discount_percentage": None,
    }

    # Playwright-specific selectors
    cookie_accept_selector: str = (
        'css=button:has-text("Alle Akzeptieren"), '
        'button[data-test="accept-all-cookies"]'
    )

    HEADERS: Dict[str, str] = {
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
    }

    # ------------------------------------------------------------------------
    # Request generation
    # ------------------------------------------------------------------------
    def start_requests(self) -> Iterator[scrapy.Request]:
        for url in self.start_urls:
            self.logger.info(f"Initiating Playwright request for {url}")
            yield scrapy.Request(
                url=url,
                headers=self.HEADERS,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_event_to_wait_for": "networkidle",
                    "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                    "page_num": 1,
                },
                callback=self.parse,
                errback=self.errback_handle_error,
                dont_filter=True,
            )

    # ------------------------------------------------------------------------
    # Parsing logic
    # ------------------------------------------------------------------------
    async def parse(self, response: Response) -> AsyncIterator[DiscountItem]:
        page: Optional[PlaywrightPage] = response.meta.get("playwright_page")
        current_page_num = response.meta.get("page_num", 1)

        if not page or page.is_closed():
            self.logger.warning(
                f"Playwright page object not available or closed for "
                f"{response.url}. Skipping parse."
            )
            return

        self.logger.info(f"Parsing page {current_page_num}: {response.url}")

        try:
            await self._handle_popups(page)
            await self._wait_for_cards(page, current_page_num)

            card_locators = await page.locator(self.card_selector).all()
            self.logger.info(
                f"Page {current_page_num}: Found {len(card_locators)} product cards."
            )

            if not card_locators and current_page_num == 1:
                self.logger.error(
                    "No product cards found on first page. "
                    "Check selector or page state."
                )
                await self._save_screenshot_and_close(
                    page, f"penny_no_locators_page_{current_page_num}.png"
                )
                return

            # -----------------------------------------------------------------
            # Item extraction loop
            # -----------------------------------------------------------------
            items_yielded_count = 0
            for i, card_locator in enumerate(card_locators):
                item = DiscountItem()
                item["source_url"] = (
                    self.start_urls[0] if self.start_urls else response.url
                )

                try:
                    # Extract data
                    item_data = await self._extract_item_data(card_locator, response)

                    # Copy into the item
                    for field, value in item_data.items():
                        if value is not None:
                            item[field] = value

                    # Compute discount %
                    if (
                        "discount_percentage" not in item_data
                        and "original_price" in item_data
                        and "sale_price" in item_data
                    ):
                        original = self._parse_price(item_data["original_price"])
                        sale = self._parse_price(item_data["sale_price"])
                        if original and sale and original > 0:
                            item["discount_percentage"] = (
                                f"{round(((original - sale) / original) * 100)}%"
                            )

                    # Yield if essentials present
                    if item.get("url") and item.get("name"):
                        yield item
                        items_yielded_count += 1
                    else:
                        self.logger.debug(
                            f"Skipping item #{i + 1} due to missing essentials"
                        )

                except Exception as extraction_err:
                    self.logger.error(
                        f"Error extracting data for item #{i + 1}: {extraction_err}"
                    )
                    continue

            self.logger.info(
                f"Page {current_page_num}: Yielded {items_yielded_count} items."
            )

            # -----------------------------------------------------------------
            # Pagination
            # -----------------------------------------------------------------
            next_button_selector = "css=li[data-test='pagination-next']"
            disabled_next_button_selector = (
                "css=li[data-test='pagination-next'].ws-list-item--disabled"
            )

            has_next_disabled = (
                await page.locator(disabled_next_button_selector).count() > 0
            )
            has_next_button = await page.locator(next_button_selector).count() > 0

            if has_next_button and not has_next_disabled:
                next_page_num = current_page_num + 1
                next_page_url = self._get_next_page_url(response.url, next_page_num)
                self.logger.info(
                    f"Proceeding to page {next_page_num}: {next_page_url}"
                )

                yield scrapy.Request(
                    url=next_page_url,
                    headers=self.HEADERS,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_event_to_wait_for": "networkidle",
                        "playwright_context_kwargs": {
                            "extra_http_headers": self.HEADERS
                        },
                        "page_num": next_page_num,
                    },
                    callback=self.parse,
                    errback=self.errback_handle_error,
                    dont_filter=True,
                )
            else:
                self.logger.info(f"No more pages. Finished at page {current_page_num}")

            await self._close_page(page)

        except Exception as parse_err:
            self.logger.error(
                f"General error during parse for page {current_page_num}: {parse_err}"
            )
            await self._save_screenshot_and_close(
                page, f"penny_parse_error_page_{current_page_num}.png"
            )
            await self._close_page(page)

    # ------------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------------
    async def _wait_for_cards(self, page: PlaywrightPage, current_page_num: int):
        self.logger.info(
            f"Waiting for product cards with selector: {self.card_selector}"
        )
        try:
            await page.locator(self.card_selector).first.wait_for(
                state="visible", timeout=30_000
            )
            self.logger.info("Product cards are visible.")
            await page.wait_for_timeout(1_000)
        except PlaywrightTimeoutError:
            self.logger.error(
                f"Timeout waiting for product cards on page {current_page_num}."
            )
            raise
        except Exception as wait_err:
            if "closed" in str(wait_err).lower():
                self.logger.warning("Page closed during card wait.")
            raise

    async def _extract_item_data(
        self, card_locator: Locator, response: Response
    ) -> Dict[str, Any]:
        item_data: Dict[str, Any] = {}
        valid_fields = [
            "url",
            "name",
            "size",
            "validity_dates",
            "sale_price",
            "original_price",
            "discount_percentage",
            "source_url",
        ]

        for field, locator_str in self.field_locators.items():
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
                        raw_data = await locator.first.get_attribute("href", timeout=2_000)
                    else:
                        try:
                            raw_data = await locator.first.text_content(timeout=2_000)
                        except Exception:
                            try:
                                raw_data = await locator.first.inner_text(timeout=2_000)
                            except Exception:
                                all_texts = await locator.all_text_contents()
                                raw_data = (
                                    " ".join(t.strip() for t in all_texts if t.strip())
                                    if all_texts
                                    else None
                                )

                if raw_data:
                    cleaned = self._clean_data(field, raw_data)
                    if cleaned is not None:
                        item_data[field] = cleaned
                        if field in ("sale_price", "original_price"):
                            self.logger.debug(f"Extracted {field}: {cleaned}")
            except Exception as e:
                self.logger.debug(
                    f"Could not extract '{field}' with '{locator_str}': {e}"
                )

        # Absolute URL
        if item_data.get("url"):
            item_data["url"] = response.urljoin(item_data["url"])
            item_data["product_url"] = item_data["url"]

        # Required fields
        item_data["title"] = item_data.get("name", "")

        # Price fallback
        if "sale_price" in item_data:
            item_data["price"] = item_data["sale_price"]
            self.logger.debug(f"Setting price to sale_price: {item_data['price']}")
        elif "original_price" in item_data:
            item_data["price"] = item_data["original_price"]
            self.logger.debug(
                f"Setting price to original_price: {item_data['price']}"
            )
        else:
            item_data["price"] = None
            self.logger.debug("No price found in item_data")

        item_data["store_name"] = "Penny"
        item_data["source"] = "penny.at"
        return item_data

    # ------------------------------------------------------------------------
    async def _handle_popups(self, page: PlaywrightPage):
        if page.is_closed():
            return

        self.logger.debug("Checking for cookie pop-ups...")
        try:
            cookie_button = page.locator(self.cookie_accept_selector).first
            if await cookie_button.is_visible(timeout=15_000):
                self.logger.info("Cookie banner found – clicking accept.")
                await cookie_button.click(timeout=5_000, force=True)
                await page.wait_for_timeout(1_500)
            else:
                self.logger.debug("Cookie banner not visible.")
        except Exception as e:
            if "closed" not in str(e).lower():
                self.logger.warning(f"Could not click cookie button: {e}")

    # ------------------------------------------------------------------------
    def _clean_data(self, field_name: str, raw_data: str) -> Optional[str]:
        if not raw_data:
            return None

        cleaned = raw_data.replace("\xa0", " ").strip()
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if not cleaned:
            return None

        if field_name in ("sale_price", "original_price"):
            self.logger.debug(f"Cleaning price: {raw_data}")
            cleaned = cleaned.replace("€", "").replace("*", "").strip()
            cleaned = re.sub(r"(Statt|statt)[:\s]*", "", cleaned, flags=re.I)
            cleaned = re.sub(r"[^\d,.]", "", cleaned).strip()

            if "," in cleaned:
                cleaned = cleaned.replace(",", ".")
            cleaned = cleaned.strip(".")

            try:
                float(cleaned)
            except ValueError:
                self.logger.warning(f"Invalid price format after cleaning: {cleaned}")
                return None

        elif field_name == "validity_dates":
            cleaned = cleaned.replace("\n", " ")
            cleaned = re.sub(r"\s+", " ", cleaned).strip()

        elif field_name == "size":
            m = re.search(
                r"([\d,.]+)\s*(liter|l|kg|g|ml|stück|stk)", cleaned, re.I
            )
            if m:
                cleaned = f"{m.group(1)} {m.group(2).lower()}"

        return cleaned or None

    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        if not price_str:
            return None
        try:
            return float(price_str)
        except ValueError:
            return None

    # ------------------------------------------------------------------------
    def _get_next_page_url(self, current_url: str, next_page_num: int) -> str:
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query)
        qs["page"] = [str(next_page_num)]
        new_query = urlencode(qs, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    # ------------------------------------------------------------------------
    # Error handling & teardown
    # ------------------------------------------------------------------------
    async def errback_handle_error(self, failure):
        request = failure.request
        page: Optional[PlaywrightPage] = request.meta.get("playwright_page")
        page_num = request.meta.get("page_num", "unknown")

        self.logger.error(
            f"Request failed for URL: {request.url} (Page: {page_num}) "
            f"type={failure.type} value={failure.value}"
        )

        if page and not page.is_closed():
            await self._save_screenshot_and_close(
                page, f"penny_errback_page_{page_num}_{self.name}.png"
            )

    async def _close_page(self, page: Optional[PlaywrightPage]):
        if page and not page.is_closed():
            try:
                await page.context.close()
                self.logger.info("Playwright context closed.")
            except Exception as e:
                self.logger.error(f"Error closing Playwright context: {e}")

    async def _save_screenshot_and_close(
        self, page: Optional[PlaywrightPage], filename="error_screenshot.png"
    ):
        if page and not page.is_closed():
            try:
                await page.screenshot(path=filename, full_page=True)
                self.logger.info(f"Screenshot saved: {filename}")
            except Exception as img_err:
                self.logger.error(f"Failed to save screenshot {filename}: {img_err}")
            await self._close_page(page)
