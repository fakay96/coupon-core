"""
Spider for Moebelix sale pages.
"""

from .base import BaseDealsSpider

class MoebelixSpider(BaseDealsSpider):
    """Spider for Moebelix sale pages."""
    name = "moebelix"
    allowed_domains = ["www.moebelix.at"]
    start_urls = [
        "https://www.moebelix.at/c/sale",
        "https://www.moebelix.at/c/aktionen",
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
