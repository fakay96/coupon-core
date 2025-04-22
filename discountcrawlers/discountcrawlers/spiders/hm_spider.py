"""
Spider for H&M sale pages.
"""

from .base import BaseDealsSpider

class HMSpider(BaseDealsSpider):
    """Spider for H&M sale pages."""
    name = "hm"
    allowed_domains = ["www2.hm.com"]
    start_urls = [
        "https://www2.hm.com/en_at/sale/women/view-all.html",
        "https://www2.hm.com/en_at/sale/men/view-all.html",
    ]
    pagination_type = "page_param"
    page_param = "page"
    max_pages = 50
    card_selector = "li.product-item"
    field_selectors = {
        "url": "a.product-item-link::attr(href)",
        "name": ".product-item-heading::text",
        "price_current": ".product-item-price__price--original::text",
        "price_original": ".product-item-price__price--del::text",
        "discount_percentage": ".product-item-price__discount::text",
    }
