#!/usr/bin/env python3
"""
Test script for Firecrawl integration
====================================

This script tests the Firecrawl integration using the official API endpoints
and request/response structures as documented at https://docs.firecrawl.dev
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add the discountcrawlers directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'discountcrawlers'))

from discountcrawlers.firecrawl_integration import (
    FirecrawlConfig, 
    FirecrawlClient, 
    FirecrawlRequest,
    FirecrawlDiscountExtractor
)

# Load API key from environment
API_KEY = os.getenv('FIRECRAWL_API_KEY')
if not API_KEY:
    print("❌ FIRECRAWL_API_KEY environment variable not set")
    print("Please set your Firecrawl API key:")
    print("export FIRECRAWL_API_KEY='fc-your-api-key-here'")
    sys.exit(1)

async def test_basic_scraping():
    """Test basic URL scraping functionality."""
    print("\n🔍 Testing Basic Scraping...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=30,
        max_retries=3
    )
    
    async with FirecrawlClient(config) as client:
        # Test with a simple, reliable URL
        test_url = "https://httpbin.org/html"
        
        request = FirecrawlRequest(
            url=test_url,
            formats=["markdown", "html"],
            only_main_content=True
        )
        
        try:
            result = await client.scrape_url(request)
            
            if result.get("success"):
                print("✅ Basic scraping successful!")
                data = result.get("data", {})
                print(f"   - Markdown length: {len(data.get('markdown', ''))} chars")
                print(f"   - HTML length: {len(data.get('html', ''))} chars")
                print(f"   - Title: {data.get('metadata', {}).get('title', 'N/A')}")
                return True
            else:
                print(f"❌ Basic scraping failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Basic scraping error: {e}")
            return False

async def test_actions():
    """Test actions functionality."""
    print("\n🎭 Testing Actions...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=60,
        max_retries=3
    )
    
    async with FirecrawlClient(config) as client:
        # Test with a simple page that has interactive elements
        test_url = "https://httpbin.org/forms/post"
        
        actions = [
            {"type": "wait", "milliseconds": 2000},
            {"type": "scrape"}
        ]
        
        request = FirecrawlRequest(
            url=test_url,
            formats=["markdown", "html"],
            actions=actions,
            wait_for_timeout=3000
        )
        
        try:
            result = await client.scrape_url(request)
            
            if result.get("success"):
                print("✅ Actions test successful!")
                data = result.get("data", {})
                print(f"   - Content extracted with actions")
                print(f"   - Markdown length: {len(data.get('markdown', ''))} chars")
                return True
            else:
                print(f"❌ Actions test failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Actions test error: {e}")
            return False

async def test_crawling():
    """Test crawling functionality."""
    print("\n🕷️ Testing Crawling...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=60,
        max_retries=3
    )
    
    async with FirecrawlClient(config) as client:
        # Test with a simple site
        test_url = "https://httpbin.org"
        
        try:
            # Start a crawl job
            crawl_result = await client.crawl_url(
                url=test_url,
                limit=3,
                scrape_options={
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            )
            
            if crawl_result.get("success"):
                crawl_id = crawl_result.get("id")
                print(f"✅ Crawl job started successfully! ID: {crawl_id}")
                
                # Check status (may take time to complete)
                print("   - Checking crawl status...")
                status_result = await client.check_crawl_status(crawl_id)
                
                if status_result.get("status"):
                    print(f"   - Crawl status: {status_result.get('status')}")
                    print(f"   - Total pages: {status_result.get('total', 'N/A')}")
                    print(f"   - Completed: {status_result.get('completed', 'N/A')}")
                    return True
                else:
                    print(f"❌ Status check failed: {status_result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Crawl job failed: {crawl_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Crawling test error: {e}")
            return False

async def test_discount_extraction():
    """Test discount data extraction."""
    print("\n💰 Testing Discount Extraction...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=60,
        max_retries=3
    )
    
    async with FirecrawlClient(config) as client:
        extractor = FirecrawlDiscountExtractor(client)
        
        # Test with a simple product page (using a mock page)
        test_url = "https://httpbin.org/html"
        store_name = "test_store"
        
        try:
            item = await extractor.extract_discount_data(test_url, store_name)
            
            if item:
                print("✅ Discount extraction successful!")
                print(f"   - URL: {item.get('url', 'N/A')}")
                print(f"   - Source: {item.get('source', 'N/A')}")
                print(f"   - Name: {item.get('name', 'N/A')}")
                print(f"   - Price: {item.get('price', 'N/A')}")
                print(f"   - Original Price: {item.get('original_price', 'N/A')}")
                print(f"   - Discount: {item.get('discount_percentage', 'N/A')}%")
                print(f"   - Images: {len(item.get('image_urls', []))}")
                return True
            else:
                print("❌ Discount extraction returned no data")
                return False
                
        except Exception as e:
            print(f"❌ Discount extraction error: {e}")
            return False

async def test_json_extraction():
    """Test JSON extraction with schema."""
    print("\n📋 Testing JSON Extraction...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=60,
        max_retries=3
    )
    
    async with FirecrawlClient(config) as client:
        # Test with a simple page
        test_url = "https://httpbin.org/html"
        
        # Define a simple schema for extraction
        json_options = {
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "has_forms": {"type": "boolean"}
                }
            }
        }
        
        request = FirecrawlRequest(
            url=test_url,
            formats=["json"],
            json_options=json_options,
            only_main_content=True
        )
        
        try:
            result = await client.scrape_url(request)
            
            if result.get("success"):
                print("✅ JSON extraction successful!")
                data = result.get("data", {})
                json_data = data.get("json", {})
                print(f"   - Extracted JSON: {json.dumps(json_data, indent=2)}")
                return True
            else:
                print(f"❌ JSON extraction failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ JSON extraction error: {e}")
            return False

async def test_error_handling():
    """Test error handling with invalid URLs."""
    print("\n🚨 Testing Error Handling...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=30,
        max_retries=2
    )
    
    async with FirecrawlClient(config) as client:
        # Test with an invalid URL
        invalid_url = "https://this-domain-does-not-exist-12345.com"
        
        request = FirecrawlRequest(
            url=invalid_url,
            formats=["markdown"]
        )
        
        try:
            result = await client.scrape_url(request)
            
            if not result.get("success"):
                print("✅ Error handling working correctly!")
                print(f"   - Expected failure for invalid URL")
                return True
            else:
                print("❌ Should have failed for invalid URL")
                return False
                
        except Exception as e:
            print(f"✅ Exception caught as expected: {type(e).__name__}")
            return True

async def main():
    """Run all tests."""
    print("🚀 Starting Firecrawl Integration Tests")
    print("=" * 50)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:] if len(API_KEY) > 14 else '***'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        ("Basic Scraping", test_basic_scraping),
        ("Actions", test_actions),
        ("Crawling", test_crawling),
        ("Discount Extraction", test_discount_extraction),
        ("JSON Extraction", test_json_extraction),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Firecrawl integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 