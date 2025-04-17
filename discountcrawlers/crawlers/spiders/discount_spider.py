"""
crawlers.spiders.discountspider

Defines DiscountSpider, a Scrapy spider that uses Splash to fully scroll
through the "Angebote" (offers) catalogue on fromaustria.com, then extracts
every product deal as a DiscountItem. Now supports pagination using the correct URL format.
"""

from __future__ import annotations
from datetime import datetime
from typing import Set
import re

import scrapy
from scrapy_splash import SplashRequest

from crawlers.items import DiscountItem


class DiscountSpider(scrapy.Spider):
    """
    A Splash‑powered Scrapy spider named "discountspider".

    Workflow:
      1. Start with the first page of Angebote.
      2. For each page (1-10):
         a. Load the page via Splash.
         b. Repeatedly scroll to the bottom until no new product cards appear
            (three consecutive identical counts) or MAX_SCROLLS is reached.
         c. Parse every <li class="productCard"> in the final HTML.
         d. Yield a DiscountItem for each unique product URL, with all fields
            populated and a UTC timestamp.
         e. Move to the next page if available.
    """

    name = "discountspider"
    allowed_domains = ["fromaustria.com"]
    start_urls = ["https://www.fromaustria.com/de-AT/angebote"]
    MAX_SCROLLS = 40  # Max scroll attempts before assuming page is fully loaded
    MAX_PAGES = 10    # Maximum number of pagination pages to crawl

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the spider.

        Creates a set to track which product URLs have already been seen,
        ensuring that each deal is only yielded once.
        """
        super().__init__(*args, **kwargs)
        self.seen_urls: Set[str] = set()
        self.current_page = 1

    def get_lua_script(self) -> str:
        """
        Return the Lua script used for scrolling, with MAX_SCROLLS properly inserted.
        """
        return f"""
        function main(splash, args)
          splash:set_viewport_size(1920,1080)
          splash.private_mode_enabled = false
          splash:set_user_agent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            .. '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
          assert(splash:go(args.url))
          splash:wait(2)

          -- Accept cookie banner if present
          local consent = splash:select('button[data-testid="uc-accept-all-button"]')
          if consent then
            consent:mouse_click()
            splash:wait(1)
          end

          -- Scroll until no new products load or MAX_SCROLLS reached
          local unchanged, last_count = 0, 0
          for i = 1, {self.MAX_SCROLLS} do
            splash:evaljs("window.scrollTo(0, document.body.scrollHeight)")
            splash:wait(1.5)
            local count = splash:evaljs(
              "document.querySelectorAll('ul#productList li.productCard').length"
            )
            if count == last_count then
              unchanged = unchanged + 1
            else
              unchanged, last_count = 0, count
            end
            if unchanged >= 3 then
              break
            end
          end

          return {{ html = splash:html() }}
        end
        """

    def start_requests(self):
        """
        Kick off the crawl with a single SplashRequest for the first page.
        
        The Lua script will do all the scrolling; when it finishes, parse()
        will be called with the fully‑loaded HTML.
        """
        # Start with the first page of Angebote section
        first_page_url = self.start_urls[0]
        yield SplashRequest(
            url=first_page_url,
            callback=self.parse,
            endpoint="execute",
            args={"lua_source": self.get_lua_script(), "timeout": 90.0},
            dont_filter=True,
            meta={"page": 1}
        )

    def get_next_page_url(self, current_page):
        """
        Construct the URL for the next page based on the provided format.
        For fromaustria.com, pagination follows the format:
        https://www.fromaustria.com/de-AT/suche?keyword=angebote&page=X#catalog-navbar
        """
        next_page = current_page + 1
        # Use the search URL format with 'angebote' keyword for pagination
        return f"https://www.fromaustria.com/de-AT/suche?keyword=angebote&page={next_page}#catalog-navbar"

    def parse(self, response: scrapy.http.HtmlResponse):
        """
        Extract every product deal from the final HTML snapshot.
        After processing the current page, request the next page if available.

        For each <li.productCard>:
          - Build absolute URL and skip if already seen.
          - Extract brand, name, sale_price, original_price, price_per_unit,
            discount_percentage, stock_info.
          - Stamp with current UTC time.
          - Yield as DiscountItem.

        Logs a warning if the page contains no product cards (possible layout change).
        """
        current_page = response.meta.get("page", 1)
        self.logger.info(f"Processing page {current_page}")

        cards = response.css("ul#productList > li.productCard")
        if not cards:
            self.logger.warning(f"No product cards found on page {current_page}; check page layout.")
            # Even if no cards are found, we might try to move to the next page
        else:
            new_count = 0
            for card in cards:
                url = response.urljoin(card.css(".productCard__title a::attr(href)").get())
                if url in self.seen_urls:
                    continue
                self.seen_urls.add(url)
                new_count += 1

                yield DiscountItem(
                    url=url,
                    brand=card.css(".productCard__brand::text").get(),
                    name=card.css(".productCard__title a::text").get(),
                    sale_price=card.css(
                        ".price--reduced::text, .price--default::text, "
                        ".productCard__price > span:not(.price--perUnit)::text"
                    ).get(),
                    original_price=card.css(
                        ".price--lineThrough::text, .instead-price::text"
                    ).get(),
                    price_per_unit=card.css(".price--perUnit::text").get(),
                    discount_percentage=card.css(".productCard__tags .percent::text").get(),
                    stock_info=card.css(".productCard__stock::text").get(),
                    timestamp=datetime.utcnow().isoformat(timespec="seconds"),
                )

            self.logger.info(
                f"Page {current_page}: {new_count} new items, {len(self.seen_urls)} total unique."
            )

        # Move to next page if we haven't reached MAX_PAGES
        if current_page < self.MAX_PAGES:
            next_page_url = self.get_next_page_url(current_page)
            
            self.logger.info(f"Moving to page {current_page + 1}: {next_page_url}")
            
            yield SplashRequest(
                url=next_page_url,
                callback=self.parse,
                endpoint="execute",
                args={"lua_source": self.get_lua_script(), "timeout": 90.0},
                dont_filter=True,
                meta={"page": current_page + 1}
            )
        else:
            self.logger.info(f"Reached maximum page limit ({self.MAX_PAGES}). Crawling complete.")