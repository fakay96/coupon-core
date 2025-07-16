#!/usr/bin/env python3
"""
Convert All Spiders to Firecrawl
================================

This script converts all existing spiders in the discountcrawlers project
to use Firecrawl instead of traditional Scrapy + Playwright approaches.

Usage:
    python convert_to_firecrawl.py [--spider SPIDER_NAME] [--all]

Examples:
    python convert_to_firecrawl.py --spider spar
    python convert_to_firecrawl.py --all
"""

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any


class SpiderConverter:
    """Convert spiders from traditional scraping to Firecrawl."""
    
    def __init__(self, spiders_dir: str = "discountcrawlers/spiders"):
        self.spiders_dir = Path(spiders_dir)
        self.backup_dir = self.spiders_dir / "backup"
        self.template_dir = self.spiders_dir / "templates"
        
    def get_all_spiders(self) -> List[str]:
        """Get list of all spider files."""
        spider_files = []
        for file in self.spiders_dir.glob("*_spider.py"):
            if file.name not in ["base.py", "base_firecrawl.py"]:
                spider_files.append(file.stem)
        return spider_files
    
    def backup_spider(self, spider_name: str) -> bool:
        """Create backup of original spider."""
        try:
            spider_file = self.spiders_dir / f"{spider_name}.py"
            if not spider_file.exists():
                print(f"Spider {spider_name} not found")
                return False
            
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Copy to backup
            backup_file = self.backup_dir / f"{spider_name}_original.py"
            shutil.copy2(spider_file, backup_file)
            print(f"Backed up {spider_name} to {backup_file}")
            return True
            
        except Exception as e:
            print(f"Error backing up {spider_name}: {e}")
            return False
    
    def extract_spider_info(self, spider_name: str) -> Dict[str, Any]:
        """Extract key information from existing spider."""
        spider_file = self.spiders_dir / f"{spider_name}.py"
        
        if not spider_file.exists():
            return {}
        
        content = spider_file.read_text()
        
        # Extract basic info
        info = {
            'name': spider_name,
            'original_content': content,
            'allowed_domains': self._extract_allowed_domains(content),
            'start_urls': self._extract_start_urls(content),
            'custom_settings': self._extract_custom_settings(content),
            'max_pages': self._extract_max_pages(content),
            'store_name': self._get_store_name_from_spider(spider_name)
        }
        
        return info
    
    def _extract_allowed_domains(self, content: str) -> List[str]:
        """Extract allowed_domains from spider content."""
        pattern = r'allowed_domains\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            domains_str = match.group(1)
            # Parse domains from string
            domains = []
            for domain in re.findall(r'"([^"]+)"', domains_str):
                domains.append(domain)
            return domains
        return []
    
    def _extract_start_urls(self, content: str) -> List[str]:
        """Extract start_urls from spider content."""
        pattern = r'start_urls\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            urls_str = match.group(1)
            # Parse URLs from string
            urls = []
            for url in re.findall(r'"([^"]+)"', urls_str):
                urls.append(url)
            return urls
        return []
    
    def _extract_custom_settings(self, content: str) -> Dict[str, Any]:
        """Extract custom_settings from spider content."""
        pattern = r'custom_settings\s*:\s*Dict\[str,\s*Any\]\s*=\s*\{([^}]+)\}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            settings_str = match.group(1)
            # This is a simplified extraction - in practice you'd need a proper parser
            return {'extracted': True, 'raw': settings_str}
        return {}
    
    def _extract_max_pages(self, content: str) -> int:
        """Extract max_pages from spider content."""
        pattern = r'max_pages\s*:\s*int\s*=\s*(\d+)'
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
        return 10  # Default
    
    def _get_store_name_from_spider(self, spider_name: str) -> str:
        """Get store name from spider name."""
        # Remove common suffixes
        store_name = spider_name.replace('_spider', '').replace('_firecrawl', '')
        return store_name
    
    def generate_firecrawl_spider(self, spider_info: Dict[str, Any]) -> str:
        """Generate Firecrawl spider content from spider info."""
        store_name = spider_info['store_name']
        spider_name = spider_info['name']
        
        template = f'''"""
{store_name.upper()} Spider using Firecrawl
{'=' * (len(store_name) + 25)}

This spider scrapes discount products from {store_name.upper()} using Firecrawl API
for enhanced data extraction and JavaScript rendering.

Features:
- Structured data extraction via Firecrawl
- Automatic pagination handling
- Product information extraction
- Price and discount calculation
"""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .base_firecrawl import BaseFirecrawlSpider
from ..items import DiscountItem
from ..config.settings import get_store_config


class {store_name.capitalize()}FirecrawlSpider(BaseFirecrawlSpider):
    """{store_name.upper()} spider using Firecrawl for enhanced scraping."""
    
    name = "{spider_name}_firecrawl"
    allowed_domains = {spider_info['allowed_domains']}
    start_urls = {spider_info['start_urls']}
    
    # Store-specific configuration
    store_config = get_store_config('{store_name}')
    max_pages = store_config.get('max_pages', {spider_info['max_pages']})
    items_per_page = store_config.get('items_per_page', 50)
    
    # Custom settings for {store_name.upper()}
    custom_settings = {{
        **BaseFirecrawlSpider.custom_settings,
        'DOWNLOAD_DELAY': 1.5,  # {store_name.upper()} rate limiting
        'AUTOTHROTTLE_START_DELAY': 1.5,
        'AUTOTHROTTLE_MAX_DELAY': 10,
    }}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(f"{{self.__class__.__name__}}")
    
    def _get_wait_actions(self) -> list:
        """Get wait actions specific to {store_name.upper()}."""
        return [
            {{
                "type": "wait",
                "timeout": 3000  # Wait for dynamic content
            }},
            {{
                "type": "wait_for_selector",
                "selector": ".product-card, .product-item, li[data-test*='product']",
                "timeout": 8000
            }}
        ]
    
    def _get_store_name_from_url(self, url: str) -> str:
        """Extract store name from URL."""
        return "{store_name}"
    
    async def _extract_items_from_firecrawl_result(
        self, 
        result: Dict[str, Any], 
        source_url: str, 
        store_name: str
    ) -> list[DiscountItem]:
        """Extract discount items from Firecrawl result with {store_name.upper()}-specific logic."""
        items = []
        
        try:
            # Try to extract using structured data first
            if 'data' in result and isinstance(result['data'], dict):
                structured_data = result['data']
                
                # Handle {store_name.upper()}'s product structure
                if 'products' in structured_data:
                    # Multiple products in array
                    for product_data in structured_data['products']:
                        item = self._create_{store_name}_item_from_data(product_data, source_url, store_name)
                        if item:
                            items.append(item)
                
                elif 'product' in structured_data:
                    # Single product
                    item = self._create_{store_name}_item_from_data(structured_data['product'], source_url, store_name)
                    if item:
                        items.append(item)
                
                else:
                    # Try to extract from general data structure
                    item = self._create_{store_name}_item_from_data(structured_data, source_url, store_name)
                    if item:
                        items.append(item)
            
            # Fallback: extract from content if no structured data
            if not items and 'content' in result:
                content = result['content']
                if isinstance(content, str):
                    # Use the extractor to parse content
                    item = await self.extractor.extract_discount_data(source_url, store_name)
                    if item:
                        items.append(item)
        
        except Exception as e:
            self.logger.error(f"Error extracting items from Firecrawl result: {{e}}")
        
        return items
    
    def _create_{store_name}_item_from_data(
        self, 
        data: Dict[str, Any], 
        source_url: str, 
        store_name: str
    ) -> Optional[DiscountItem]:
        """Create a DiscountItem from {store_name.upper()} data with specific field mapping."""
        try:
            item = DiscountItem()
            item['source_url'] = source_url
            item['store_name'] = store_name
            item['source'] = '{store_name}'
            
            # {store_name.upper()}-specific field mapping
            field_mapping = {{
                'name': ['name', 'title', 'product_name', 'product-title'],
                'brand': ['brand', 'manufacturer'],
                'sale_price': ['sale_price', 'current_price', 'price', 'price-current'],
                'original_price': ['original_price', 'old_price', 'regular_price', 'price-old'],
                'discount_percentage': ['discount_percentage', 'discount', 'savings'],
                'size': ['size', 'quantity', 'weight'],
                'validity_dates': ['validity_dates', 'valid_until', 'expiry'],
                'url': ['url', 'product_url', 'link'],
                'image_urls': ['image_urls', 'images', 'image'],
                'category': ['category', 'product_category']
            }}
            
            for item_field, data_fields in field_mapping.items():
                for data_field in data_fields:
                    if data_field in data and data[data_field]:
                        item[item_field] = data[data_field]
                        break
            
            # Handle image URLs
            if 'image_urls' in item and isinstance(item['image_urls'], str):
                item['image_urls'] = [item['image_urls']]
            
            # Calculate discount percentage if not provided
            if not item.get('discount_percentage') and item.get('original_price') and item.get('sale_price'):
                try:
                    original = self._parse_{store_name}_price(item['original_price'])
                    sale = self._parse_{store_name}_price(item['sale_price'])
                    if original and sale and original > 0:
                        discount = ((original - sale) / original) * 100
                        item['discount_percentage'] = f"{{discount:.1f}}%"
                except (ValueError, TypeError):
                    pass
            
            # Clean and validate the item
            item = self._clean_{store_name}_item(item)
            
            return item if self._validate_{store_name}_item(item) else None
            
        except Exception as e:
            self.logger.error(f"Error creating {store_name.upper()} item from data: {{e}}")
            return None
    
    def _parse_{store_name}_price(self, price_str: str) -> Optional[float]:
        """Parse {store_name.upper()} price format."""
        if not price_str:
            return None
        
        try:
            # Remove currency symbols and clean
            import re
            cleaned = re.sub(r'[^\\d,.]', '', str(price_str))
            
            # Handle European decimal format
            if ',' in cleaned and '.' in cleaned:
                # Format: 1.234,56 -> 1234.56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Check if comma is decimal separator
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _clean_{store_name}_item(self, item: DiscountItem) -> DiscountItem:
        """Clean and normalize {store_name.upper()} item data."""
        # Clean price fields
        for price_field in ['sale_price', 'original_price']:
            if item.get(price_field):
                item[price_field] = str(item[price_field]).strip()
        
        # Clean text fields
        for text_field in ['name', 'brand', 'size', 'category', 'validity_dates']:
            if item.get(text_field):
                item[text_field] = str(item[text_field]).strip()
        
        # Ensure URL is absolute
        if item.get('url') and not item['url'].startswith('http'):
            if item['url'].startswith('/'):
                item['url'] = f"https://www.{store_name}.at{{item['url']}}"
            else:
                item['url'] = f"https://www.{store_name}.at/{{item['url']}}"
        
        return item
    
    def _validate_{store_name}_item(self, item: DiscountItem) -> bool:
        """Validate if a {store_name.upper()} item has required fields."""
        # {store_name.upper()} items should have at least a name or sale price
        return bool(
            item.get('name') or 
            item.get('sale_price') or 
            item.get('url')
        )
    
    def _get_next_page_url(self, current_url: str, next_page_num: int) -> Optional[str]:
        """Generate next page URL for {store_name.upper()} pagination."""
        try:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            
            parsed_url = urlparse(current_url)
            query_params = parse_qs(parsed_url.query)
            
            # Update page parameter
            query_params['page'] = [str(next_page_num)]
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            next_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
            
            return next_url
            
        except Exception as e:
            self.logger.error(f"Error generating next page URL: {{e}}")
            return None
'''
        
        return template
    
    def convert_spider(self, spider_name: str) -> bool:
        """Convert a single spider to use Firecrawl."""
        try:
            print(f"Converting {spider_name} to Firecrawl...")
            
            # Backup original
            if not self.backup_spider(spider_name):
                return False
            
            # Extract spider info
            spider_info = self.extract_spider_info(spider_name)
            if not spider_info:
                print(f"Could not extract info from {spider_name}")
                return False
            
            # Generate new spider content
            new_content = self.generate_firecrawl_spider(spider_info)
            
            # Write new spider
            new_spider_file = self.spiders_dir / f"{spider_name}_firecrawl.py"
            new_spider_file.write_text(new_content)
            
            print(f"Successfully converted {spider_name} to {new_spider_file}")
            return True
            
        except Exception as e:
            print(f"Error converting {spider_name}: {e}")
            return False
    
    def convert_all_spiders(self) -> bool:
        """Convert all spiders to use Firecrawl."""
        spiders = self.get_all_spiders()
        
        if not spiders:
            print("No spiders found to convert")
            return False
        
        print(f"Found {len(spiders)} spiders to convert: {', '.join(spiders)}")
        
        success_count = 0
        for spider in spiders:
            if self.convert_spider(spider):
                success_count += 1
        
        print(f"Successfully converted {success_count}/{len(spiders)} spiders")
        return success_count == len(spiders)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Convert spiders to use Firecrawl")
    parser.add_argument("--spider", help="Convert specific spider")
    parser.add_argument("--all", action="store_true", help="Convert all spiders")
    
    args = parser.parse_args()
    
    converter = SpiderConverter()
    
    if args.spider:
        converter.convert_spider(args.spider)
    elif args.all:
        converter.convert_all_spiders()
    else:
        print("Please specify --spider SPIDER_NAME or --all")
        print("Available spiders:", ", ".join(converter.get_all_spiders()))


if __name__ == "__main__":
    main() 