"""
Spider for BIPA promotions.
"""

from .base import BaseDealsSpider

class BipaSpider(BaseDealsSpider):
    """Spider for BIPA promotions."""
    name = "bipa"
    allowed_domains = ["www.bipa.at"]
    start_urls = ["https://www.bipa.at/cp/aktionen"]
    pagination_type = "none"
    card_selector = "div.promo-offer"
    field_selectors = {
        "url": "a::attr(href)",
        "name": ".promo-offer__headline::text",
        "details": ".promo-offer__details::text",
    }
