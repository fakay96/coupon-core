"""
Spider for MediaMarkt sale pages.
"""

from .base import BaseDealsSpider

class MediaMarktSpider(BaseDealsSpider):
    """Spider for MediaMarkt sale pages."""
    name = "mediamarkt"
    allowed_domains = ["www.mediamarkt.at"]
    start_urls = ["https://www.mediamarkt.at/de/campaign/sale"]
    pagination_type = "page_param"
    page_param = "page"
    max_pages = 20
    card_selector = "div.product-wrapper"
    field_selectors = {
        "url": "a::attr(href)",
        "name": ".product-wrapper__title::text",
        "price_current": ".price__current::text",
        "price_original": ".price__old::text",
    }
