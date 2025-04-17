"""discountscraper.spiders.discount_spider
=================================================
Refactored **FromAustria** discount spider with:

* Separation of concerns – most utilities live in :pymod:`discountscraper.utils`.
* Proper static typing throughout.
* Google‑style docstrings.
* Minimal business logic in the spider itself.
* A *thin* SplashRequest builder provided by :pyfunc:`discountscraper.utils.splash.build_splash_request`.
"""

from __future__ import annotations

import logging
from typing import Generator, Iterable, Optional

import scrapy
from scrapy.selector import Selector
from scrapy.http import Response

# Local imports
from discountscraper.items import DiscountItem, DiscountData
from discountscraper.utils.price import (
    parse_discount_percentage,
    parse_euro_price,
)
from discountscraper.utils.splash import build_splash_request

_LOGGER = logging.getLogger(__name__)


class DiscountSpider(scrapy.Spider):
    """Spider scraping discounted products from *fromaustria.com*.

    The spider renders each page through **Splash** to deal with JavaScript
    and infinite scrolling. Pagination is followed until no ``Next`` button
    is found or a hard limit of ``MAX_PAGES`` is reached (to prevent
    accidental infinite crawls during testing).
    """

    name: str = "discountspider"
    allowed_domains: list[str] = ["fromaustria.com"]
    start_urls: list[str] = ["https://www.fromaustria.com/de-AT/angebote"]
    custom_settings: dict[str, object] = {
        # Avoid hitting the site too hard while still having decent speed
        "DOWNLOAD_DELAY": 0.25,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    #: Safety valve – stop after this many pages even if *Next* is present.
    MAX_PAGES: int = 10

    # ------------------------------------------------------------------ #
    # Scrapy API methods                                                 #
    # ------------------------------------------------------------------ #

    def start_requests(self) -> Iterable[scrapy.Request]:
        """Kick‑off the crawl using :pyfunc:`build_splash_request`."""
        for url in self.start_urls:
            yield build_splash_request(url, callback=self.parse, meta={"page": 1})

    def parse(self, response: Response) -> Generator[DiscountItem, None, None]:
        """Parse a single result page.

        Parameters
        ----------
        response:
            Rendered HTML page coming from Splash.
        """
        page_no = response.meta.get("page", 1)
        _LOGGER.info("Parsing page %s (%s)", page_no, response.url)

        # ----- Extract products ----------------------------------------
        products_sel = response.css("li.productCard")
        for sel in products_sel:
            item = self._extract_product(sel, response)
            if item:
                yield item

        # ----- Pagination ---------------------------------------------
        has_next = bool(response.data.get("has_next")) if hasattr(response, "data") else False
        if has_next and page_no < self.MAX_PAGES:
            _LOGGER.debug("Following pagination to page %s", page_no + 1)
            yield build_splash_request(
                response.url,
                callback=self.parse,
                meta={"page": page_no + 1},
                splash_args={"click_next": True},
                dont_filter=True,
            )

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _extract_product(self, sel: Selector, response: Response) -> Optional[DiscountItem]:
        """Return a :class:`DiscountItem` from a *productCard* ``<li>`` element.

        The heavy lifting (price parsing, percentage parsing) is delegated
        to utility functions so that this method stays *quasi‑declarative*.
        """
        data = DiscountData(
            url=response.urljoin(sel.css(".productCard__title a.productCard__link::attr(href)").get()),
            brand=sel.css(".productCard__title strong.productCard__brand::text").get(),
            name=sel.css(".productCard__title a.productCard__link::text").get(),
            sale_price=parse_euro_price(
                sel.css(".productCard__price .price--reduced::text").get()
            ),
            original_price=parse_euro_price(
                sel.css(".productCard__price .instead-price::text").get()
            ),
            price_per_unit=sel.css(".productCard__price .price--perUnit::text").get(),
            discount_percentage=parse_discount_percentage(
                sel.css(".productCard__tags .flag.sale-tag.small.percent::text").get()
            ),
            stock_info=sel.css(".productCard__stock::text").get(),
            category=response.css("h1.page-title::text").get(),
        )

        if data.sale_price is None or data.original_price is None:
            # Incomplete entry – skip silently.
            return None

        return data.to_item()
