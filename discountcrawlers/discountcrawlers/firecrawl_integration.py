"""
Firecrawl Integration for Discount Crawlers
==========================================

This module provides integration with Firecrawl API for enhanced web scraping
with structured data extraction, JavaScript rendering, and advanced parsing
capabilities.

Features:
- Structured data extraction with schemas
- JavaScript rendering and waiting
- Screenshot capture
- PDF generation
- Custom extraction rules
- Rate limiting and retry logic
- Integration with existing Scrapy pipeline

Based on official Firecrawl documentation: https://docs.firecrawl.dev
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
import requests
from urllib.parse import urlparse
from .items import DiscountItem

LOGGER = logging.getLogger(__name__)

@dataclass
class FirecrawlConfig:
    """Configuration for Firecrawl API integration."""
    api_key: str
    base_url: str = "https://api.firecrawl.dev"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    max_concurrent_requests: int = 5  # Reduced to avoid rate limits
    enable_screenshots: bool = False
    enable_pdf: bool = False
    wait_for_selectors: Optional[List[str]] = None
    wait_for_timeout: int = 5000
    extract_rules: Optional[Dict[str, Any]] = None

@dataclass
class FirecrawlRequest:
    """Request configuration for Firecrawl API."""
    url: str
    formats: List[str] = None
    actions: Optional[List[Dict[str, Any]]] = None
    wait_for_selectors: Optional[List[str]] = None
    wait_for_timeout: int = 5000
    screenshot: bool = False
    pdf: bool = False
    metadata: Optional[Dict[str, Any]] = None
    json_options: Optional[Dict[str, Any]] = None
    only_main_content: bool = False
    timeout_ms: int = 120000

class FirecrawlClient:
    """Client for interacting with Firecrawl API."""
    
    def __init__(self, config: FirecrawlConfig):
        self.config = config
        self.session = None
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_url(self, request: FirecrawlRequest) -> Dict[str, Any]:
        """Scrape a URL using Firecrawl API.
        
        Based on official docs: https://docs.firecrawl.dev/scraping
        """
        async with self._semaphore:
            payload = {
                "url": request.url,
                "formats": request.formats or ["markdown", "html"]
            }
            
            # Add optional parameters if provided
            if request.actions:
                # Fix action format to match API requirements
                fixed_actions = []
                for action in request.actions:
                    if action.get("type") == "wait":
                        # For wait actions, use either milliseconds or selector, not both
                        if "timeout" in action:
                            fixed_actions.append({
                                "type": "wait",
                                "milliseconds": action["timeout"]
                            })
                        elif "selector" in action:
                            fixed_actions.append({
                                "type": "wait",
                                "selector": action["selector"]
                            })
                    elif action.get("type") == "wait_for_selector":
                        # Convert to proper wait action
                        fixed_actions.append({
                            "type": "wait",
                            "selector": action.get("selector", "")
                        })
                    else:
                        # Keep other action types as is
                        fixed_actions.append(action)
                
                payload["actions"] = fixed_actions
            
            if request.screenshot or self.config.enable_screenshots:
                payload["screenshot"] = True
                
            if request.pdf or self.config.enable_pdf:
                payload["pdf"] = True
            
            if request.only_main_content:
                payload["onlyMainContent"] = request.only_main_content
            
            if request.timeout_ms:
                payload["timeout"] = request.timeout_ms
            
            # Note: jsonOptions is not supported in v1 API
            # We'll extract data from the content instead
            
            # Debug: Log the exact payload being sent
            LOGGER.info(f"Sending payload to Firecrawl: {json.dumps(payload, indent=2)}")
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.post(
                        f"{self.config.base_url}/v1/scrape",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            # Rate limited, wait and retry
                            error_data = await response.json()
                            error_msg = error_data.get("error", "")
                            
                            # Extract wait time from error message if available
                            if "retry after" in error_msg.lower():
                                import re
                                wait_match = re.search(r"retry after (\d+)s", error_msg.lower())
                                if wait_match:
                                    wait_time = int(wait_match.group(1)) + 2  # Add buffer
                                else:
                                    wait_time = (2 ** attempt) * self.config.retry_delay
                            else:
                                wait_time = (2 ** attempt) * self.config.retry_delay
                            
                            LOGGER.warning(f"Rate limited, waiting {wait_time}s before retry (attempt {attempt + 1})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # Debug: Log the error response
                            error_text = await response.text()
                            LOGGER.error(f"Firecrawl API error (status {response.status}): {error_text}")
                            response.raise_for_status()
                            
                except Exception as e:
                    LOGGER.error(f"Firecrawl request failed (attempt {attempt + 1}): {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
            
            raise Exception("Max retries exceeded")
    
    async def crawl_url(self, url: str, limit: int = 10, scrape_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crawl a URL and all accessible subpages.
        
        Based on official docs: https://docs.firecrawl.dev/crawling
        """
        async with self._semaphore:
            payload = {
                "url": url,
                "limit": limit
            }
            
            if scrape_options:
                payload["scrapeOptions"] = scrape_options
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.post(
                        f"{self.config.base_url}/v1/crawl",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            wait_time = (2 ** attempt) * self.config.retry_delay
                            LOGGER.warning(f"Rate limited, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                            
                except Exception as e:
                    LOGGER.error(f"Firecrawl crawl request failed (attempt {attempt + 1}): {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
            
            raise Exception("Max retries exceeded")
    
    async def check_crawl_status(self, crawl_id: str) -> Dict[str, Any]:
        """Check the status of a crawl job.
        
        Based on official docs: https://docs.firecrawl.dev/crawling
        """
        async with self._semaphore:
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.get(
                        f"{self.config.base_url}/v1/crawl/{crawl_id}"
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            wait_time = (2 ** attempt) * self.config.retry_delay
                            LOGGER.warning(f"Rate limited, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                            
                except Exception as e:
                    LOGGER.error(f"Firecrawl status check failed (attempt {attempt + 1}): {e}")
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
            
            raise Exception("Max retries exceeded")

class FirecrawlDiscountExtractor:
    """Extractor for discount information using Firecrawl."""
    
    def __init__(self, client: FirecrawlClient):
        self.client = client
        
        # Common extraction rules for discount sites using Firecrawl's extraction format
        self.discount_extraction_rules = {
            "product": {
                "selector": "h1, .product-title, .product-name, [data-testid='product-title']",
                "type": "text"
            },
            "price": {
                "selector": ".price, .product-price, [data-testid='price'], .current-price",
                "type": "text"
            },
            "original_price": {
                "selector": ".original-price, .old-price, .was-price, [data-testid='original-price']",
                "type": "text"
            },
            "discount_percentage": {
                "selector": ".discount, .discount-percentage, .sale-badge, [data-testid='discount']",
                "type": "text"
            },
            "brand": {
                "selector": ".brand, .product-brand, [data-testid='brand']",
                "type": "text"
            },
            "description": {
                "selector": ".description, .product-description, [data-testid='description']",
                "type": "text"
            },
            "images": {
                "selector": "img[src*='product'], .product-image img, [data-testid='product-image']",
                "type": "attribute",
                "attribute": "src"
            },
            "availability": {
                "selector": ".stock, .availability, [data-testid='availability']",
                "type": "text"
            }
        }
    
    async def extract_discount_data(self, url: str, store_name: str) -> Optional[DiscountItem]:
        """Extract discount data from a URL using Firecrawl."""
        try:
            # Create actions for better extraction
            actions = [
                {"type": "wait", "milliseconds": 2000},
                {"type": "scrape"}
            ]
            
            request = FirecrawlRequest(
                url=url,
                formats=["markdown", "html"],
                actions=actions,
                wait_for_selectors=None,
                wait_for_timeout=5000
            )
            
            result = await self.client.scrape_url(request)
            
            if not result.get("success"):
                LOGGER.error(f"Firecrawl extraction failed for {url}: {result.get('error')}")
                return None
            
            data = result.get("data", {})
            markdown_content = data.get("markdown", "")
            html_content = data.get("html", "")
            metadata = data.get("metadata", {})
            
            # Create DiscountItem from extracted data
            item = DiscountItem()
            item['url'] = url
            item['source'] = store_name
            item['name'] = self._extract_from_content(markdown_content, "product")
            item['title'] = self._extract_from_content(markdown_content, "product")
            item['description'] = self._extract_from_content(markdown_content, "description")
            item['brand'] = self._extract_from_content(markdown_content, "brand")
            item['price'] = self._clean_price(self._extract_from_content(markdown_content, "price"))
            item['original_price'] = self._clean_price(self._extract_from_content(markdown_content, "original_price"))
            item['discount_percentage'] = self._extract_discount_percentage(self._extract_from_content(markdown_content, "discount_percentage"))
            item['stock_info'] = self._extract_from_content(markdown_content, "availability")
            item['image_urls'] = self._extract_images(html_content)
            item['crawled_at'] = datetime.utcnow().isoformat()
            
            # Calculate discount percentage if not provided
            if not item['discount_percentage'] and item['price'] and item['original_price']:
                try:
                    original = float(item['original_price'])
                    current = float(item['price'])
                    if original > current:
                        item['discount_percentage'] = round(((original - current) / original) * 100, 2)
                except (ValueError, ZeroDivisionError):
                    pass
            
            return item
            
        except Exception as e:
            LOGGER.error(f"Error extracting discount data from {url}: {e}")
            return None
    
    def _extract_from_content(self, content: str, field_type: str) -> str:
        """Extract specific field from markdown content using simple patterns."""
        if not content:
            return ""
        
        # Simple extraction patterns based on common markdown structures
        patterns = {
            "product": [
                r"#\s*(.+?)(?:\n|$)",
                r"\*\*(.+?)\*\*.*?Price",
                r"Product:\s*(.+?)(?:\n|$)"
            ],
            "price": [
                r"Price:\s*\$?([\d,]+\.?\d*)",
                r"\$?([\d,]+\.?\d*)\s*(?:USD|EUR|GBP)",
                r"Current Price:\s*\$?([\d,]+\.?\d*)"
            ],
            "original_price": [
                r"Original Price:\s*\$?([\d,]+\.?\d*)",
                r"Was:\s*\$?([\d,]+\.?\d*)",
                r"List Price:\s*\$?([\d,]+\.?\d*)"
            ],
            "discount_percentage": [
                r"(\d+(?:\.\d+)?)\s*% off",
                r"Save\s*(\d+(?:\.\d+)?)\s*%",
                r"Discount:\s*(\d+(?:\.\d+)?)\s*%"
            ],
            "brand": [
                r"Brand:\s*(.+?)(?:\n|$)",
                r"by\s+(.+?)(?:\n|$)"
            ],
            "description": [
                r"Description:\s*(.+?)(?:\n\n|\n#|$)",
                r"About this item:\s*(.+?)(?:\n\n|\n#|$)"
            ],
            "availability": [
                r"In Stock",
                r"Available",
                r"Out of Stock",
                r"Unavailable"
            ]
        }
        
        import re
        field_patterns = patterns.get(field_type, [])
        
        for pattern in field_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
        
        return ""
    
    def _extract_images(self, html_content: str) -> List[str]:
        """Extract image URLs from HTML content."""
        if not html_content:
            return []
        
        import re
        # Simple regex to extract img src attributes
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, html_content)
        
        # Filter for product images
        product_images = [img for img in matches if any(keyword in img.lower() for keyword in ['product', 'item', 'image'])]
        return product_images[:5]  # Limit to 5 images
    
    def _clean_price(self, price_str: str) -> Optional[float]:
        """Clean and convert price string to float."""
        if not price_str:
            return None
        
        # Remove currency symbols and non-numeric characters except decimal point
        import re
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        
        # Handle different decimal separators
        if ',' in cleaned and '.' in cleaned:
            # European format: 1.234,56 -> 1234.56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned:
            # Check if comma is decimal separator
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def _extract_discount_percentage(self, discount_str: str) -> Optional[float]:
        """Extract discount percentage from string."""
        if not discount_str:
            return None
        
        import re
        # Look for percentage patterns
        match = re.search(r'(\d+(?:\.\d+)?)\s*%', discount_str)
        if match:
            return float(match.group(1))
        
        # Look for "save X" patterns
        match = re.search(r'save\s+(\d+(?:\.\d+)?)\s*%', discount_str.lower())
        if match:
            return float(match.group(1))
        
        return None

# Utility functions
def get_store_specific_rules(store_name: str) -> Dict[str, Any]:
    """Get store-specific extraction rules for Firecrawl structured data extraction."""
    
    # Base rules that work for most e-commerce sites
    base_rules = {
        "products": {
            "selector": "div[data-test*='product'], .product-card, .product-item, li[data-test*='product'], .productBox",
            "type": "list",
            "output": {
                "name": {
                    "selector": "h1, h2, h3, .product-name, .product-title, [data-test*='title'], .mainTitleProd",
                    "type": "text"
                },
                "brand": {
                    "selector": ".brand, .manufacturer, [data-test*='brand']",
                    "type": "text"
                },
                "sale_price": {
                    "selector": ".price, .current-price, .sale-price, [data-test*='price'], .priceInteger, .priceDecimal",
                    "type": "text"
                },
                "original_price": {
                    "selector": ".original-price, .old-price, .was-price, .insteadOfPrice, del, .price-old",
                    "type": "text"
                },
                "discount_percentage": {
                    "selector": ".discount, .discount-badge, .savings, .discount-percentage",
                    "type": "text"
                },
                "url": {
                    "selector": "a[href*='product'], a[data-test*='link'], a[href]",
                    "type": "attribute",
                    "attribute": "href"
                },
                "image_urls": {
                    "selector": "img[src*='product'], img[data-test*='image'], img[src]",
                    "type": "attribute",
                    "attribute": "src"
                },
                "size": {
                    "selector": ".size, .quantity, .weight, .product-size",
                    "type": "text"
                },
                "category": {
                    "selector": ".category, .product-category, .breadcrumb",
                    "type": "text"
                },
                "validity_dates": {
                    "selector": ".validity, .valid-until, .expiry, [data-test*='validity']",
                    "type": "text"
                }
            }
        }
    }
    
    # Store-specific rules
    store_rules = {
        "spar": {
            "products": {
                "selector": "div.productBox[data-url]",
                "type": "list",
                "output": {
                    "name": {
                        "selector": "div.productTitle:not(.mainTitleProd)",
                        "type": "text"
                    },
                    "brand": {
                        "selector": "div.productTitle.mainTitleProd",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": "label.priceInteger, label.priceDecimal",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": "label.insteadOfPrice",
                        "type": "text"
                    },
                    "price_per_unit": {
                        "selector": "label.extraInfoPrice",
                        "type": "text"
                    },
                    "url": {
                        "selector": "self",
                        "type": "attribute",
                        "attribute": "data-url"
                    }
                }
            }
        },
        "penny": {
            "products": {
                "selector": "li[data-test='product-tile']",
                "type": "list",
                "output": {
                    "name": {
                        "selector": "h3[data-test='product-title']",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": "div[data-test='product-price'] strong, div[data-test='product-price'] span.price-current",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": "div[data-test='product-price'] del, div[data-test='product-price'] span.price-old",
                        "type": "text"
                    },
                    "size": {
                        "selector": "ul[data-test='product-information-piece-description'] li",
                        "type": "text"
                    },
                    "validity_dates": {
                        "selector": "div[data-test='product-price-validity']",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[data-test='product-tile-link']",
                        "type": "attribute",
                        "attribute": "href"
                    }
                }
            }
        },
        "mueller": {
            "products": {
                "selector": ".product-item, .product-card",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3, h4",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "xxxlutz": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "zalando": {
            "products": {
                "selector": ".product-card, [data-testid*='product']",
                "type": "list",
                "output": {
                    "name": {
                        "selector": "[data-testid='product-title'], .product-name, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": "[data-testid='brand'], .brand",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": "[data-testid='price'], .price, .current-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "ikea": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "mediamarkt": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "hm": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "adidas": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "billa": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "bipa": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "lidl": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "ca": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "moebelix": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        },
        "moemax": {
            "products": {
                "selector": ".product-card, .product-item",
                "type": "list",
                "output": {
                    "name": {
                        "selector": ".product-name, .product-title, h3",
                        "type": "text"
                    },
                    "brand": {
                        "selector": ".brand, .manufacturer",
                        "type": "text"
                    },
                    "sale_price": {
                        "selector": ".price, .current-price, .sale-price",
                        "type": "text"
                    },
                    "original_price": {
                        "selector": ".original-price, .old-price, .was-price, del",
                        "type": "text"
                    },
                    "discount_percentage": {
                        "selector": ".discount, .discount-badge, .savings",
                        "type": "text"
                    },
                    "url": {
                        "selector": "a[href*='product'], a[href]",
                        "type": "attribute",
                        "attribute": "href"
                    },
                    "image_urls": {
                        "selector": "img[src]",
                        "type": "attribute",
                        "attribute": "src"
                    }
                }
            }
        }
    }
    
    # Return store-specific rules if available, otherwise base rules
    return store_rules.get(store_name.lower(), base_rules) 