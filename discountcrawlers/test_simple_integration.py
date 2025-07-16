#!/usr/bin/env python3
"""
Simple test of the integration code
==================================
"""

import asyncio
import os
import sys

# Add the discountcrawlers directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'discountcrawlers'))

from discountcrawlers.firecrawl_integration import (
    FirecrawlConfig, 
    FirecrawlClient, 
    FirecrawlRequest
)

# Load API key from environment
API_KEY = os.getenv('FIRECRAWL_API_KEY', 'fc-072741aa600f4082aa21c2c8a773dfed')

async def test_simple_integration():
    """Test the integration with minimal setup."""
    print("🔍 Testing simple integration...")
    
    config = FirecrawlConfig(
        api_key=API_KEY,
        timeout=60,
        max_retries=3,
        max_concurrent_requests=1
    )
    
    print(f"Config: {config}")
    
    async with FirecrawlClient(config) as client:
        print("✅ Client created successfully")
        
        request = FirecrawlRequest(
            url="https://httpbin.org/html",
            formats=["markdown", "html"]
        )
        
        print(f"Request: {request}")
        
        try:
            result = await client.scrape_url(request)
            
            if result.get("success"):
                print("✅ Integration successful!")
                data = result.get("data", {})
                print(f"   - Markdown length: {len(data.get('markdown', ''))} chars")
                return True
            else:
                print(f"❌ Integration failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Integration error: {e}")
            return False

async def main():
    """Run the test."""
    print("🚀 Simple Integration Test")
    print("=" * 30)
    
    success = await test_simple_integration()
    
    if success:
        print("\n🎉 Integration is working!")
    else:
        print("\n❌ Integration failed!")

if __name__ == "__main__":
    asyncio.run(main()) 