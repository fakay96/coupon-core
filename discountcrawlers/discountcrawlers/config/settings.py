"""
Configuration settings for discount crawlers.

This module contains all configuration settings including API keys,
database connections, and other environment-specific settings.
"""

import os
from typing import Optional

# Firecrawl API Configuration
FIRECRAWL_API_KEY: str = os.getenv('FIRECRAWL_API_KEY', '')

# Database Configuration
DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///discounts.db')

# Logging Configuration
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT: str = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'

# Scrapy Settings
SCRAPY_SETTINGS = {
    'BOT_NAME': 'discountcrawlers',
    'SPIDER_MODULES': ['discountcrawlers.spiders'],
    'NEWSPIDER_MODULE': 'discountcrawlers.spiders',
    'ROBOTSTXT_OBEY': False,
    'CONCURRENT_REQUESTS': 1,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    'DOWNLOAD_DELAY': 1,
    'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
    'COOKIES_ENABLED': False,
    'TELNETCONSOLE_ENABLED': False,
    'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
    'TWISTED_REACTOR': 'twisted.internet.asyncioreactor.AsyncioSelectorReactor',
    'FEED_EXPORT_ENCODING': 'utf-8',
    'AUTOTHROTTLE_ENABLED': True,
    'AUTOTHROTTLE_START_DELAY': 1,
    'AUTOTHROTTLE_MAX_DELAY': 10,
    'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
    'AUTOTHROTTLE_DEBUG': False,
    'HTTPERROR_ALLOWED_CODES': [403, 429, 500, 502, 503, 504],
}

# Firecrawl-specific settings
FIRECRAWL_SETTINGS = {
    'timeout': 60,
    'max_retries': 3,
    'retry_delay': 2.0,
    'max_concurrent_requests': 1,
    'enable_screenshots': False,
    'enable_pdf': False,
    'wait_for_timeout': 10000,
}

# Store-specific configurations
STORE_CONFIGS = {
    'spar': {
        'max_pages': 20,
        'items_per_page': 80,
        'wait_for_selectors': ['div.productBox'],
    },
    'penny': {
        'max_pages': 15,
        'items_per_page': 50,
        'wait_for_selectors': ['li[data-test="product-tile"]'],
    },
    'mueller': {
        'max_pages': 10,
        'items_per_page': 40,
        'wait_for_selectors': ['.product-item'],
    },
    'xxxlutz': {
        'max_pages': 12,
        'items_per_page': 60,
        'wait_for_selectors': ['.product-card'],
    },
    'zalando': {
        'max_pages': 8,
        'items_per_page': 72,
        'wait_for_selectors': ['.product-card'],
    },
}

def get_store_config(store_name: str) -> dict:
    """Get configuration for a specific store."""
    return STORE_CONFIGS.get(store_name.lower(), {})

def validate_config() -> bool:
    """Validate that required configuration is present."""
    if not FIRECRAWL_API_KEY:
        print("Warning: FIRECRAWL_API_KEY not set")
        return False
    return True