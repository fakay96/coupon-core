#!/usr/bin/env python3
"""
Test Firecrawl Spiders
======================

This script tests the new Firecrawl-based spiders to ensure they work correctly
and can extract data from the stores.

Usage:
    python test_firecrawl_spiders.py [--spider SPIDER_NAME] [--all]
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import re

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from discountcrawlers.firecrawl_integration import (
    FirecrawlClient, 
    FirecrawlConfig, 
    FirecrawlRequest,
    get_store_specific_rules
)
from discountcrawlers.config.settings import FIRECRAWL_API_KEY


class HTMLProductExtractor:
    """Extract product data from HTML using BeautifulSoup."""
    
    def __init__(self):
        self.store_selectors = {
            'spar': {
                'product_containers': 'div.productBox[data-url]',
                'name': 'div.productTitle:not(.mainTitleProd)',
                'brand': 'div.productTitle.mainTitleProd',
                'sale_price': 'label.priceInteger, label.priceDecimal',
                'original_price': 'label.insteadOfPrice',
                'price_per_unit': 'label.extraInfoPrice',
                'url': 'data-url'  # Attribute on the container
            },
            'penny': {
                'product_containers': 'li[data-test="product-tile"]',
                'name': 'h3[data-test="product-title"]',
                'sale_price': 'div[data-test="product-price"] strong, div[data-test="product-price"] span.price-current',
                'original_price': 'div[data-test="product-price"] del, div[data-test="product-price"] span.price-old',
                'size': 'ul[data-test="product-information-piece-description"] li',
                'validity_dates': 'div[data-test="product-price-validity"]',
                'url': 'a[data-test="product-tile-link"]'
            },
            'mueller': {
                'product_containers': '.product-item, .product-card, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, h4, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings, .discount-percentage',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'xxxlutz': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'zalando': {
                'product_containers': '.product-card, [data-testid*="product"], .product-tile',
                'name': '[data-testid="product-title"], .product-name, h3, [data-testid*="title"]',
                'brand': '[data-testid="brand"], .brand, [data-testid*="brand"]',
                'sale_price': '[data-testid="price"], .price, .current-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'ikea': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'mediamarkt': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'hm': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'adidas': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'billa': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'bipa': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'lidl': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'ca': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'moebelix': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            },
            'moemax': {
                'product_containers': '.product-card, .product-item, .product-tile, [data-testid*="product"]',
                'name': '.product-name, .product-title, h3, [data-testid*="title"]',
                'brand': '.brand, .manufacturer, [data-testid*="brand"]',
                'sale_price': '.price, .current-price, .sale-price, [data-testid*="price"]',
                'original_price': '.original-price, .old-price, .was-price, del, .price-old',
                'discount_percentage': '.discount, .discount-badge, .savings',
                'url': 'a[href*="product"], a[href]',
                'image_urls': 'img[src]'
            }
        }
    
    def extract_products_from_html(self, html_content: str, store_name: str) -> List[Dict[str, Any]]:
        """Extract products from HTML content using store-specific selectors."""
        if store_name not in self.store_selectors:
            print(f"No selectors defined for store: {store_name}")
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        selectors = self.store_selectors[store_name]
        products = []
        
        # Find all product containers
        containers = soup.select(selectors['product_containers'])
        print(f"Found {len(containers)} product containers")
        
        # If no containers found, try alternative selectors
        if not containers:
            print("No containers found with primary selectors, trying alternatives...")
            alternative_selectors = [
                'article', '.item', '.product', '[class*="product"]', 
                '[class*="item"]', '[class*="card"]', 'li', '.tile'
            ]
            for alt_selector in alternative_selectors:
                containers = soup.select(alt_selector)
                if containers:
                    print(f"Found {len(containers)} containers with alternative selector: {alt_selector}")
                    break
        
        # If still no containers, try to extract any promotional content
        if not containers:
            print("No product containers found, extracting promotional content...")
            return self.extract_promotional_content(soup, store_name)
        
        for i, container in enumerate(containers[:5]):  # Limit to first 5 for testing
            product = {}
            
            # Extract product name
            if 'name' in selectors:
                name_elem = container.select_one(selectors['name'])
                if name_elem:
                    product['name'] = name_elem.get_text(strip=True)
            
            # Extract brand
            if 'brand' in selectors:
                brand_elem = container.select_one(selectors['brand'])
                if brand_elem:
                    product['brand'] = brand_elem.get_text(strip=True)
            
            # Extract sale price
            if 'sale_price' in selectors:
                price_elem = container.select_one(selectors['sale_price'])
                if price_elem:
                    product['sale_price'] = price_elem.get_text(strip=True)
            
            # Extract original price
            if 'original_price' in selectors:
                orig_price_elem = container.select_one(selectors['original_price'])
                if orig_price_elem:
                    product['original_price'] = orig_price_elem.get_text(strip=True)
            
            # Extract price per unit
            if 'price_per_unit' in selectors:
                unit_elem = container.select_one(selectors['price_per_unit'])
                if unit_elem:
                    product['price_per_unit'] = unit_elem.get_text(strip=True)
            
            # Extract size
            if 'size' in selectors:
                size_elem = container.select_one(selectors['size'])
                if size_elem:
                    product['size'] = size_elem.get_text(strip=True)
            
            # Extract validity dates
            if 'validity_dates' in selectors:
                validity_elem = container.select_one(selectors['validity_dates'])
                if validity_elem:
                    product['validity_dates'] = validity_elem.get_text(strip=True)
            
            # Extract discount percentage
            if 'discount_percentage' in selectors:
                discount_elem = container.select_one(selectors['discount_percentage'])
                if discount_elem:
                    product['discount_percentage'] = discount_elem.get_text(strip=True)
            
            # Extract URL
            if 'url' in selectors:
                if selectors['url'] == 'data-url':
                    # URL is stored as data attribute on container
                    product['url'] = container.get('data-url', '')
                else:
                    # URL is in a link element
                    url_elem = container.select_one(selectors['url'])
                    if url_elem:
                        product['url'] = url_elem.get('href', '')
            
            # Extract image URLs
            if 'image_urls' in selectors:
                img_elem = container.select_one(selectors['image_urls'])
                if img_elem:
                    product['image_urls'] = img_elem.get('src', '')
            
            # Try to extract any text content if no specific fields found
            if not product:
                # Extract any text that might be product info
                text_content = container.get_text(strip=True)
                if len(text_content) > 10 and len(text_content) < 200:  # Reasonable length for product info
                    product['raw_content'] = text_content
            
            # Only add product if it has at least a name, price, or raw content
            if product.get('name') or product.get('sale_price') or product.get('raw_content'):
                products.append(product)
                print(f"Product {i+1}: {product}")
        
        # If no products were extracted from containers, try promotional content
        if not products:
            print("No products extracted from containers, trying promotional content...")
            return self.extract_promotional_content(soup, store_name)
        
        return products
    
    def extract_promotional_content(self, soup: BeautifulSoup, store_name: str) -> List[Dict[str, Any]]:
        """Extract promotional content when no structured products are found."""
        promotional_items = []
        
        # Look for promotional keywords in text content
        promotional_keywords = [
            'angebot', 'sale', 'rabatt', 'discount', 'reduziert', 'reduced', 
            'sparen', 'save', 'günstig', 'cheap', 'preis', 'price', 'euro', '€',
            'aktion', 'promotion', 'schnäppchen', 'bargain', 'reduziert', 'reduced'
        ]
        
        # First, try to extract any meaningful content from the page
        page_title = soup.find('title')
        if page_title:
            title_text = page_title.get_text(strip=True)
            if title_text and len(title_text) > 5:
                promotional_items.append({
                    'type': 'page_title',
                    'content': title_text,
                    'store': store_name
                })
        
        # Look for any text that might indicate the page content
        body_text = soup.get_text(strip=True)
        if body_text and len(body_text) > 50:
            # Extract first 200 characters as page summary
            summary = body_text[:200] + "..." if len(body_text) > 200 else body_text
            promotional_items.append({
                'type': 'page_summary',
                'content': summary,
                'store': store_name
            })
        
        # Find all text elements that might contain promotional content
        text_elements = soup.find_all(['p', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        for elem in text_elements:
            text = elem.get_text(strip=True).lower()
            if any(keyword in text for keyword in promotional_keywords):
                # Check if this element has a reasonable length
                if 10 < len(text) < 300:
                    item = {
                        'type': 'promotional_content',
                        'content': elem.get_text(strip=True),
                        'element_type': elem.name,
                        'store': store_name
                    }
                    
                    # Try to find associated links
                    parent = elem.parent
                    if parent:
                        links = parent.find_all('a', href=True)
                        if links:
                            item['related_links'] = [link.get('href') for link in links[:3]]
                    
                    promotional_items.append(item)
                    print(f"Promotional content: {item}")
        
        # Also look for any links that might be to product pages
        product_links = soup.find_all('a', href=True)
        for link in product_links[:10]:  # Limit to first 10
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if link might be to a product page
            if any(keyword in href.lower() or keyword in text.lower() 
                   for keyword in ['product', 'artikel', 'item', 'shop', 'buy', 'kaufen']):
                if len(text) > 3:  # Reasonable link text
                    item = {
                        'type': 'product_link',
                        'text': text,
                        'url': href,
                        'store': store_name
                    }
                    promotional_items.append(item)
                    print(f"Product link: {item}")
        
        # If still no content found, try to extract any navigation or menu items
        if not promotional_items:
            nav_elements = soup.find_all(['nav', 'menu', 'ul', 'ol'])
            for nav in nav_elements[:5]:
                links = nav.find_all('a', href=True)
                for link in links[:3]:
                    text = link.get_text(strip=True)
                    if len(text) > 2:
                        item = {
                            'type': 'navigation_link',
                            'text': text,
                            'url': link.get('href'),
                            'store': store_name
                        }
                        promotional_items.append(item)
                        print(f"Navigation link: {item}")
        
        return promotional_items


class FirecrawlSpiderTester:
    """Test Firecrawl spiders."""
    
    def __init__(self):
        self.config = FirecrawlConfig(
            api_key=FIRECRAWL_API_KEY,
            timeout=60,
            max_retries=2,
            retry_delay=1.0,
            max_concurrent_requests=1,
            enable_screenshots=False,
            enable_pdf=False,
            wait_for_timeout=5000,
        )
        self.client = FirecrawlClient(self.config)
        self.html_extractor = HTMLProductExtractor()
        
        # Test URLs for different stores
        self.test_urls = {
            'spar': 'https://www.interspar.at/shop/lebensmittel/search/?query=*&q=*&hitsPerPage=10&page=1&filter=is-on-promotion:true',
            'penny': 'https://www.penny.at/angebote',
            'mueller': 'https://www.mueller.at/',
            'xxxlutz': 'https://www.xxxlutz.at/angebote',
            'zalando': 'https://www.zalando.at/',
            'ikea': 'https://www.ikea.com/at/de/',
            'mediamarkt': 'https://www.mediamarkt.at/',
            'hm': 'https://www2.hm.com/at_de/sale.html',
            'adidas': 'https://www.adidas.at/outlet',
            'billa': 'https://shop.billa.at/',
            'bipa': 'https://www.bipa.at/',
            'lidl': 'https://www.lidl.at/',
            'ca': 'https://www.hofer.at/',
            'moebelix': 'https://www.moebelix.at/',
            'moemax': 'https://www.moemax.at/'
        }
    
    async def test_store(self, store_name: str) -> Dict[str, Any]:
        """Test a specific store."""
        print(f"\n{'='*50}")
        print(f"Testing {store_name.upper()}")
        print(f"{'='*50}")
        
        if store_name not in self.test_urls:
            print(f"No test URL available for {store_name}")
            return {'success': False, 'error': 'No test URL available'}
        
        url = self.test_urls[store_name]
        print(f"URL: {url}")
        
        try:
            # Get store-specific extraction rules (for reference, not used in API call)
            extraction_rules = get_store_specific_rules(store_name)
            print(f"Extraction rules: {json.dumps(extraction_rules, indent=2)}")
            
            # Create Firecrawl request
            request = FirecrawlRequest(
                url=url,
                formats=["markdown", "html"],
                actions=[
                    {"type": "wait", "milliseconds": 3000},
                    {"type": "wait", "selector": ".product-card, .product-item, li[data-test*='product']"}
                ],
                wait_for_timeout=5000,
                screenshot=False,
                pdf=False,
                only_main_content=True,
                timeout_ms=60000
            )
            
            # Test the request
            async with self.client as client:
                print("Sending request to Firecrawl...")
                result = await client.scrape_url(request)
                
                if not result:
                    return {'success': False, 'error': 'No result from Firecrawl'}
                
                print(f"Firecrawl response status: {result.get('success', 'unknown')}")
                
                # Extract products from HTML content
                if 'data' in result and 'html' in result['data']:
                    html_content = result['data']['html']
                    print(f"\nExtracting products from HTML content...")
                    
                    # Parse HTML and extract products
                    products = self.html_extractor.extract_products_from_html(html_content, store_name)
                    
                    if products:
                        print(f"\nSuccessfully extracted {len(products)} products!")
                        return {
                            'success': True,
                            'products_count': len(products),
                            'sample_product': products[0] if products else None,
                            'all_products': products
                        }
                    else:
                        print("No products found in HTML content")
                        # Debug: Print a sample of the HTML to understand the structure
                        print(f"\n--- HTML Sample (first 2000 chars) ---")
                        print(html_content[:2000])
                        print(f"--- End HTML Sample ---")
                        return {
                            'success': False,
                            'error': 'No products found in HTML content'
                        }
                else:
                    print("No HTML content found in Firecrawl response")
                    return {
                        'success': False,
                        'error': 'No HTML content found'
                    }
        
        except Exception as e:
            print(f"Error testing {store_name}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_all_stores(self) -> Dict[str, Dict[str, Any]]:
        """Test all stores."""
        results = {}
        
        for store_name in self.test_urls.keys():
            result = await self.test_store(store_name)
            results[store_name] = result
            
            # Add a small delay between tests
            await asyncio.sleep(1)
        
        return results
    
    def print_summary(self, results: Dict[str, Dict[str, Any]]):
        """Print a summary of test results."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        successful = 0
        failed = 0
        
        for store_name, result in results.items():
            status = "✅ SUCCESS" if result.get('success') else "❌ FAILED"
            products_count = result.get('products_count', 0)
            error = result.get('error', '')
            
            print(f"{store_name.upper():<15} {status:<12} Products: {products_count}")
            if error:
                print(f"  Error: {error}")
        
        successful = sum(1 for r in results.values() if r.get('success'))
        failed = len(results) - successful
        
        print(f"\nTotal: {len(results)} stores")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(successful/len(results)*100):.1f}%")


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Firecrawl spiders")
    parser.add_argument("--spider", help="Test specific spider")
    parser.add_argument("--all", action="store_true", help="Test all spiders")
    
    args = parser.parse_args()
    
    if not FIRECRAWL_API_KEY:
        print("Error: FIRECRAWL_API_KEY not set")
        return
    
    tester = FirecrawlSpiderTester()
    
    if args.spider:
        result = await tester.test_store(args.spider)
        print(f"\nResult: {json.dumps(result, indent=2, default=str)}")
    elif args.all:
        results = await tester.test_all_stores()
        tester.print_summary(results)
        
        # Save results to file
        with open('firecrawl_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to firecrawl_test_results.json")
    else:
        print("Please specify --spider SPIDER_NAME or --all")
        print("Available spiders:", ", ".join(tester.test_urls.keys()))


if __name__ == "__main__":
    asyncio.run(main()) 