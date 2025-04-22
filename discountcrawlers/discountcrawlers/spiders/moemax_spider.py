"""
Spider for Mömax sale pages.
"""

from .base import BaseDealsSpider

class MoemaxSpider(BaseDealsSpider):
    """Spider for Mömax sale pages."""
    name = "moemax"
    allowed_domains = ["www.moemax.at"]
    start_urls = [
        "https://www.moemax.at/c/sale",
        "https://www.moemax.at/c/pink-shopping",
    ]
    pagination_type = "page_param"
    page_param = "page"
    max_pages = 20
    card_selector = "div.product-tile"
    field_selectors = {
        "url": "a::attr(href)",
        "name": ".product-title::text",
        "price_current": ".product-price__current::text",
        "price_original": ".product-price__old::text",
    }
