"""
Spider for Billa promotions.
"""

from .base import BaseDealsSpider

class BillaSpider(BaseDealsSpider):
    """Spider for Billa promotions."""
    name = "billa"
    allowed_domains = ["shop.billa.at"]
    start_urls = ["https://shop.billa.at/aktionen"]
    pagination_type = "none"
    card_selector = "div.teaser-box"
    field_selectors = {
        "url": "a.teaser-box__link::attr(href)",
        "name": "h3.teaser-box__title::text",
        "price_current": ".product-item-price-current::text",
        "price_original": ".product-item-price-old::text",
        "discount_percentage": ".badge-aktion::text",
    }
