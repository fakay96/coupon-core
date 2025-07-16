"""
Spider for scraping product deals from XXXLutz Austria sale pages using Scrapy and Playwright.
Extracts dynamic content, handles modals, cleans data, and navigates via pagination.
"""
import re
from typing import AsyncIterator, ClassVar, Dict, Optional

import scrapy
from scrapy.http import Response
from scrapy.exceptions import CloseSpider
from scrapy_playwright.page import PageMethod
from playwright.async_api import Page as PlaywrightPage

from .base import BaseDealsSpider
from discountcrawlers.items import DiscountItem


class XXXLutzSpider(BaseDealsSpider):
    """
    Spider for scraping XXXLutz Austria online sale listings.

    Uses Playwright to render JavaScript, dismiss modals, extract product details,
    and handle pagination up to a configured page limit.
    """
    name: ClassVar[str] = "xxxlutz"
    allowed_domains: ClassVar[list[str]] = ["www.xxxlutz.at"]
    start_urls: ClassVar[list[str]] = ["https://www.xxxlutz.at/c/online-sale/"]

    card_selector_xpath: ClassVar[str] = (
        "//article[.//a[@data-purpose='productTile.link.product']]"
        " | //div[.//a[@data-purpose='productTile.link.product']]"
    )
    field_locators: ClassVar[Dict[str, str]] = {
        "url": ".//a[@data-purpose='productTile.link.product']",
        "brand": ".//div[@data-testid='productCard.subtitle']",
        "name": ".//a[@data-purpose='productTile.link.product']/h3",
        "sale_price": ".//div[@data-purpose='product.price.current']",
        "original_price": ".//span[@data-purpose='originalPrice']",
        "discount_percentage": ".//span[@data-purpose='discountBadge']",
        "price_per_unit": ".//div[@data-purpose='pricePerUnit']",
    }
    next_page_selector: ClassVar[str] = (
        "button[aria-label=\"Nächste Seite\"], a[title=\"Nächste Seite\"]"
    )

    max_pages: ClassVar[int] = 30
    requires_js: ClassVar[bool] = True
    custom_settings: ClassVar[Dict[str, object]] = {
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
    HEADERS: ClassVar[Dict[str, str]] = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/123.0.0.0 Safari/537.36'
        ),
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;q=0.9,'
            'image/avif,image/webp,image/apng,*/*;q=0.8,'
            'application/signed-exchange;v=b3;q=0.7'
        ),
        'Accept-Language': 'en-GB,en;q=0.9,de-AT;q=0.8,de;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'Sec-CH-UA': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }

    def start_requests(self) -> scrapy.Request:
        """
        Yield the initial Playwright-enabled requests for all configured start URLs.
        """
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                headers=self.HEADERS,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_event_to_wait_for": "domcontentloaded",
                    "playwright_context_kwargs": {"extra_http_headers": self.HEADERS},
                    "page_num": 1,
                },
                callback=self.parse,
                errback=self.errback_handle_error,
                dont_filter=True,
            )

    async def parse(self, response: Response) -> AsyncIterator[DiscountItem]:
        """
        Render the page, handle modals, extract product data, and paginate.
        """
        page: Optional[PlaywrightPage] = response.meta.get("playwright_page")
        page_num: int = response.meta.get("page_num", 1)

        if not page or page.is_closed():
            raise CloseSpider(f"No Playwright page for {response.url}")

        await self._handle_modals(page)
        await page.locator(f"xpath={self.card_selector_xpath}").first.wait_for(
            state='visible', timeout=35_000
        )
        await page.wait_for_timeout(1_500)

        cards = await page.locator(f"xpath={self.card_selector_xpath}").all()

        for locator in cards:
            item = DiscountItem()
            item['source_url'] = response.url
            for field, xpath in self.field_locators.items():
                element = locator.locator(f"xpath={xpath}")
                if await element.count() == 0:
                    item[field] = None
                    continue
                if field == 'url':
                    raw = await element.first.get_attribute('href')
                else:
                    raw = await element.first.inner_text()
                item[field] = self._clean_data(field, raw) if raw else None

            if url := item.get('url'):
                item['url'] = response.urljoin(url.strip())

            if item.get('url') and (item.get('name') or item.get('brand')):
                yield item

        if page_num < self.max_pages:
            async for req in self._paginate(page, page_num, response):
                yield req
        else:
            await self._close_page(page)

    async def _handle_modals(self, page: PlaywrightPage) -> None:
        """
        Dismiss country and cookie modals if present.
        """
        selectors = [
            'button:has-text("Weiter einkaufen")',
            'button#onetrust-accept-btn-handler'
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=7_000):
                    await locator.click(timeout=5_000)
                    await page.wait_for_timeout(1_500)
            except Exception:
                continue

    def _clean_data(self, field: str, raw: str) -> Optional[str]:
        """
        Clean raw text for price, discount, or general fields.
        """
        text = raw.replace('\xa0', ' ').strip()
        text = re.sub(r'\s+', ' ', text)
        if not text:
            return None
        if field in ('sale_price', 'original_price'):
            text = re.sub(r'(UVP|Stattpreis)[:\s]*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'[€*‒]', '', text).strip()
            text = re.sub(r'\s*/\s*[\w.]+$', '', text).strip()
            text = re.sub(r'[^\d,.-]', '', text)
            if ',' in text:
                if '.' in text and text.rfind('.') > text.rfind(','):
                    text = text.replace(',', '')
                else:
                    text = text.replace('.', '').replace(',', '.')
        elif field == 'discount_percentage':
            text = re.sub(r'[^\d]', '', text)
        return text or None

    async def _paginate(
        self,
        page: PlaywrightPage,
        page_num: int,
        response: Response
    ) -> AsyncIterator[scrapy.Request]:
        """
        Click next page and yield a new request until the page limit.
        """
        button = page.locator(self.next_page_selector).first
        if await button.count() and await button.is_enabled(timeout=5_000):
            await button.scroll_into_view_if_needed()
            await button.click(timeout=15_000)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2_000)
            new_url = page.url
            yield scrapy.Request(
                url=new_url,
                headers=self.HEADERS,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_event_to_wait_for': 'domcontentloaded',
                    'playwright_context_kwargs': {'extra_http_headers': self.HEADERS},
                    'page_num': page_num + 1,
                },
                callback=self.parse,
                errback=self.errback_handle_error,
                dont_filter=True,
            )
        else:
            await self._close_page(page)

    async def errback_handle_error(self, failure) -> None:
        """
        Log request errors, capture a screenshot, and close the Playwright page.
        """
        request = failure.request
        page: Optional[PlaywrightPage] = request.meta.get('playwright_page')
        response = getattr(failure.value, 'response', None)
        if response:
            self.logger.error(f"Error {response.status} at {request.url}")
        if page and not page.is_closed():
            filename = f"xxxlutz_error_{self.name}.png"
            await page.screenshot(path=filename, full_page=True)
            await self._close_page(page)

    async def _close_page(self, page: PlaywrightPage) -> None:
        """
        Safely close the Playwright page and its context.
        """
        try:
            await page.context.close()
        except Exception:
            pass

    async def _save_screenshot_and_close(
        self,
        page: PlaywrightPage,
        filename: str = 'error.png'
    ) -> None:
        """
        Save a screenshot to the given filename and close the page.
        """
        try:
            await page.screenshot(path=filename, full_page=True)
        except Exception:
            pass
        await self._close_page(page)
