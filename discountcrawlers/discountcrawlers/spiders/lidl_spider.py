"""
Stub for Lidl flyer parsing.
"""

import scrapy
import logging

class LidlSpider(scrapy.Spider):
    """Stub for Lidl flyer parsing."""
    name = "lidl"
    allowed_domains = ["lidl.at"]
    start_urls = ["https://www.lidl.at/c/flugblatt"]

    def parse(self, response):
        """Log that specialized parsing is required."""
        logging.warning("Lidl requires PDF or JS parsing; not implemented.")
