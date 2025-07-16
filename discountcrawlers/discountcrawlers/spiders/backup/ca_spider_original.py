"""
Spider for C&A sale pages.
"""

from .base import BaseDealsSpider

class CASpider(BaseDealsSpider):
    """Spider for C&A sale pages."""
    name = "c_and_a"
    allowed_domains = ["www.c-and-a.com"]
    start_urls = [
        "https://www.c-and-a.com/at/de/shop/sale-damen",
        "https://www.c-and-a.com/at/de/shop/sale-herren",
    ]
    pagination_type = "page_param"
    page_param = "page"
    max_pages = 30
    card_selector = "article.product-tile"
    field_selectors = {
        "url": "a::attr(href)",
        "name": ".product-tile__name::text",
        "price_current": ".product-tile__price--new::text",
        "price_original": ".product-tile__price--old::text",
    }
