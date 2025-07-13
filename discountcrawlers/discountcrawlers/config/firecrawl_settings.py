"""
Firecrawl Configuration Settings
===============================

Configuration settings for Firecrawl API integration.
"""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Firecrawl API Configuration
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
FIRECRAWL_BASE_URL = os.getenv('FIRECRAWL_BASE_URL', 'https://api.firecrawl.dev')
FIRECRAWL_TIMEOUT = int(os.getenv('FIRECRAWL_TIMEOUT', '30'))
FIRECRAWL_MAX_RETRIES = int(os.getenv('FIRECRAWL_MAX_RETRIES', '3'))
FIRECRAWL_RETRY_DELAY = float(os.getenv('FIRECRAWL_RETRY_DELAY', '1.0'))
FIRECRAWL_MAX_CONCURRENT = int(os.getenv('FIRECRAWL_MAX_CONCURRENT', '10'))

# Feature flags
FIRECRAWL_ENABLE_SCREENSHOTS = os.getenv('FIRECRAWL_ENABLE_SCREENSHOTS', 'false').lower() == 'true'
FIRECRAWL_ENABLE_PDF = os.getenv('FIRECRAWL_ENABLE_PDF', 'false').lower() == 'true'

# Default wait settings
FIRECRAWL_WAIT_TIMEOUT = int(os.getenv('FIRECRAWL_WAIT_TIMEOUT', '5000'))
FIRECRAWL_WAIT_SELECTORS = os.getenv('FIRECRAWL_WAIT_SELECTORS', '.product-title,.price,.product-price').split(',')

# Store-specific extraction rules
STORE_EXTRACTION_RULES: Dict[str, Dict[str, Any]] = {
    "spar": {
        "product": {"selector": ".product-name, h1", "type": "text"},
        "price": {"selector": ".current-price, .price", "type": "text"},
        "original_price": {"selector": ".original-price, .old-price", "type": "text"},
        "brand": {"selector": ".brand-name, .brand", "type": "text"},
        "description": {"selector": ".product-description, .description", "type": "text"},
        "images": {"selector": ".product-image img, img[src*='product']", "type": "attribute", "attribute": "src"},
        "availability": {"selector": ".stock, .availability", "type": "text"},
        "discount_percentage": {"selector": ".discount-badge, .discount", "type": "text"}
    },
    "penny": {
        "product": {"selector": ".product-title, h1", "type": "text"},
        "price": {"selector": ".price, .current-price", "type": "text"},
        "original_price": {"selector": ".original-price, .was-price", "type": "text"},
        "brand": {"selector": ".brand, .product-brand", "type": "text"},
        "description": {"selector": ".product-description", "type": "text"},
        "images": {"selector": ".product-image img", "type": "attribute", "attribute": "src"},
        "discount_percentage": {"selector": ".discount-badge, .discount", "type": "text"}
    },
    "zalando": {
        "product": {"selector": "[data-testid='product-title'], h1", "type": "text"},
        "price": {"selector": "[data-testid='price'], .price", "type": "text"},
        "original_price": {"selector": "[data-testid='original-price'], .original-price", "type": "text"},
        "brand": {"selector": "[data-testid='brand'], .brand", "type": "text"},
        "description": {"selector": "[data-testid='description'], .description", "type": "text"},
        "images": {"selector": "[data-testid='product-image'], img[src*='product']", "type": "attribute", "attribute": "src"},
        "discount_percentage": {"selector": "[data-testid='discount'], .discount", "type": "text"}
    },
    "mueller": {
        "product": {"selector": ".product-name, h1", "type": "text"},
        "price": {"selector": ".price, .current-price", "type": "text"},
        "original_price": {"selector": ".original-price, .old-price", "type": "text"},
        "brand": {"selector": ".brand, .product-brand", "type": "text"},
        "description": {"selector": ".product-description", "type": "text"},
        "images": {"selector": ".product-image img", "type": "attribute", "attribute": "src"},
        "discount_percentage": {"selector": ".discount, .discount-badge", "type": "text"}
    }
}

# Store-specific wait selectors
STORE_WAIT_SELECTORS: Dict[str, List[str]] = {
    "spar": [".product-name", ".current-price", ".product-image"],
    "penny": [".product-title", ".price", ".product-image"],
    "zalando": ["[data-testid='product-title']", "[data-testid='price']", "[data-testid='product-image']"],
    "mueller": [".product-name", ".price", ".product-image"]
}

# Rate limiting settings per store
STORE_RATE_LIMITS: Dict[str, Dict[str, int]] = {
    "spar": {"requests_per_minute": 30, "delay_between_requests": 2},
    "penny": {"requests_per_minute": 25, "delay_between_requests": 2.5},
    "zalando": {"requests_per_minute": 20, "delay_between_requests": 3},
    "mueller": {"requests_per_minute": 30, "delay_between_requests": 2}
}

# Fallback settings
FIRECRAWL_FALLBACK_TO_TRADITIONAL = os.getenv('FIRECRAWL_FALLBACK_TO_TRADITIONAL', 'true').lower() == 'true'
FIRECRAWL_LOG_FAILURES = os.getenv('FIRECRAWL_LOG_FAILURES', 'true').lower() == 'true'

# Performance settings
FIRECRAWL_BATCH_SIZE = int(os.getenv('FIRECRAWL_BATCH_SIZE', '10'))
FIRECRAWL_CONCURRENT_BATCHES = int(os.getenv('FIRECRAWL_CONCURRENT_BATCHES', '2'))

# Error handling
FIRECRAWL_ALLOWED_ERROR_CODES = [403, 429, 500, 502, 503, 504]
FIRECRAWL_RETRY_ON_ERROR_CODES = [429, 500, 502, 503, 504]

def get_store_config(store_name: str) -> Dict[str, Any]:
    """Get complete configuration for a specific store."""
    store_name_lower = store_name.lower()
    
    return {
        "extraction_rules": STORE_EXTRACTION_RULES.get(store_name_lower, {}),
        "wait_selectors": STORE_WAIT_SELECTORS.get(store_name_lower, FIRECRAWL_WAIT_SELECTORS),
        "rate_limits": STORE_RATE_LIMITS.get(store_name_lower, {"requests_per_minute": 20, "delay_between_requests": 3}),
        "timeout": FIRECRAWL_TIMEOUT,
        "max_retries": FIRECRAWL_MAX_RETRIES,
        "retry_delay": FIRECRAWL_RETRY_DELAY
    }

def is_firecrawl_enabled() -> bool:
    """Check if Firecrawl is enabled (API key is configured)."""
    return bool(FIRECRAWL_API_KEY)

def get_firecrawl_config() -> Dict[str, Any]:
    """Get the complete Firecrawl configuration."""
    return {
        "api_key": FIRECRAWL_API_KEY,
        "base_url": FIRECRAWL_BASE_URL,
        "timeout": FIRECRAWL_TIMEOUT,
        "max_retries": FIRECRAWL_MAX_RETRIES,
        "retry_delay": FIRECRAWL_RETRY_DELAY,
        "max_concurrent_requests": FIRECRAWL_MAX_CONCURRENT,
        "enable_screenshots": FIRECRAWL_ENABLE_SCREENSHOTS,
        "enable_pdf": FIRECRAWL_ENABLE_PDF,
        "wait_for_selectors": FIRECRAWL_WAIT_SELECTORS,
        "wait_for_timeout": FIRECRAWL_WAIT_TIMEOUT,
        "fallback_to_traditional": FIRECRAWL_FALLBACK_TO_TRADITIONAL,
        "log_failures": FIRECRAWL_LOG_FAILURES,
        "batch_size": FIRECRAWL_BATCH_SIZE,
        "concurrent_batches": FIRECRAWL_CONCURRENT_BATCHES
    } 