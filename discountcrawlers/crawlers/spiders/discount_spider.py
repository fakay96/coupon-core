import re
from typing import Set

import scrapy
from scrapy_splash import SplashRequest

from crawlers.items import DiscountItem


class DiscountSpider(scrapy.Spider):
    """
    Scrape the “Angebote” catalogue on fromaustria.com with Splash,
    deduplicate items by URL (so exports stay clean) but **always**
    walk through every page until the list ends.
    """

    name = "discountspider"
    allowed_domains = ["fromaustria.com"]
    start_urls = ["https://www.fromaustria.com/de-AT/angebote"]
    MAX_PAGES = 10        # hard ceiling ‑‑ raise if the shop grows

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seen_urls: Set[str] = set()

    # ───────────────────────── Splash Lua ────────────────────────────
    lua_script = """
    function main(splash, args)
        splash:set_viewport_size(1920, 1080)
        splash.private_mode_enabled = false
        splash:set_user_agent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            .. '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
        assert(splash:go(args.url))
        splash:wait(3)

        local consent = splash:select('button[data-testid="uc-accept-all-button"]')
        if consent then consent:mouse_click(); splash:wait(2) end

        for i = 1, 8 do
            splash:evaljs("window.scrollBy(0, document.body.scrollHeight / 8)")
            splash:wait(1)
        end
        splash:wait(2)

        return { html = splash:html() }
    end
    """

    # ─────────────────────── initial request ─────────────────────────
    def start_requests(self):
        first = self.start_urls[0] + "?page=1"
        yield SplashRequest(
            first,
            self.parse,
            endpoint="execute",
            args={"lua_source": self.lua_script, "timeout": 90},
            meta={"page": 1},
            dont_filter=True,
        )

    # ─────────────────────────── parsing ─────────────────────────────
    def parse(self, response):
        page_no = response.meta["page"]
        products = response.css("ul#productList > li.productCard")

        # if the shop returns an empty page, we're done
        if not products:
            self.logger.info("Page %s is empty → stopping crawl.", page_no)
            return

        new_on_page = 0
        for prod in products:
            link = response.urljoin(prod.css(".productCard__title a::attr(href)").get())
            if link in self.seen_urls:               # duplicate? just skip it
                continue
            self.seen_urls.add(link)
            new_on_page += 1

            item = DiscountItem()
            item["url"] = link
            item["brand"] = prod.css(".productCard__brand::text").get()
            item["name"] = prod.css(".productCard__title a::text").get()

            price_sel = (
                ".productCard__price .price--reduced::text, "
                ".productCard__price .price--default::text, "
                ".productCard__price > span:not(.price--perUnit)::text"
            )
            item["sale_price"] = prod.css(price_sel).get()
            item["original_price"] = prod.css(
                ".price--lineThrough::text, .instead-price::text"
            ).get()
            item["price_per_unit"] = prod.css(".price--perUnit::text").get()
            item["discount_percentage"] = prod.css(
                ".productCard__tags .percent::text"
            ).get()

            if (
                not item["discount_percentage"]
                and item["sale_price"]
                and item["original_price"]
            ):
                try:
                    sp = float(item["sale_price"].replace("€", "").replace(",", ".").strip())
                    op = float(item["original_price"].replace("€", "").replace(",", ".").strip())
                    item["discount_percentage"] = f"{round(100 * (1 - sp / op))}%"
                except ValueError:
                    pass

            item["stock_info"] = prod.css(".productCard__stock::text").get()

            if item["sale_price"]:
                yield item

        self.logger.info(
            "Page %s: %d new items (total unique %d)",
            page_no, new_on_page, len(self.seen_urls)
        )

        # ── pagination: keep going unless we've hit the safety limit ──
        if page_no >= self.MAX_PAGES:
            self.logger.warning("Reached MAX_PAGES=%s, stopping crawl.", self.MAX_PAGES)
            return

        next_page = page_no + 1
        next_url = f"https://www.fromaustria.com/de-AT/angebote?page={next_page}#catalog-navbar"
        self.logger.info(
            next_url
        )
        yield SplashRequest(
            next_url,
            self.parse,
            endpoint="execute",
            args={"lua_source": self.lua_script, "timeout": 90},
            meta={"page": next_page},
            dont_filter=True,
        )
