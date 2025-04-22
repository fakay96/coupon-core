"""
Spider for Adidas outlet pages.
"""

from .base import BaseDealsSpider

class AdidasSpider(BaseDealsSpider):
    """Spider for Adidas outlet pages."""
    name = "adidas"
    allowed_domains = ["www.adidas.at"]
    start_urls = [
        "https://www.adidas.at/women-outlet",
        "https://www.adidas.at/men-outlet",
    ]
    pagination_type = "page_param"
    page_param = "page"
    max_pages = 30
    card_selector = "div.gl-product-card"
    field_selectors = {
        "url": "a::attr(href)",
        "name": ".gl-product-card__name::text",
        "price_current": ".gl-price-item--sale::text",
        "price_original": ".gl-price-item--original::text",
        "discount_percentage": ".gl-price-item--discount::text",
    }
