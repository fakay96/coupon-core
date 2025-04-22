"""
Spider for IKEA offers via infinite scroll.
"""

from .base import BaseDealsSpider

class IkeaSpider(BaseDealsSpider):
    """Spider for IKEA offers via infinite scroll."""
    name = "ikea"
    allowed_domains = ["www.ikea.com"]
    start_urls = [
        "https://www.ikea.com/at/de/offers/",
        "https://www.ikea.com/at/de/offers/new-lower-price/",
        "https://www.ikea.com/at/de/offers/last-chance/",
    ]
    pagination_type = "infinite_scroll"
    card_selector = "div.product-compact"
    field_selectors = {
        "url": "a::attr(href)",
        "name": ".product-compact__name::text",
        "price_current": ".product-compact__price .pip-price::text",
        "price_original": ".product-compact__price .pip-price--old::text",
        "discount_percentage": ".product-compact__badge-discount::text",
    }
