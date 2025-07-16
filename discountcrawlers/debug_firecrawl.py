#!/usr/bin/env python3
"""
Debug script for Firecrawl API
==============================

This script makes a simple request to understand the exact API requirements.
"""

import asyncio
import json
import os
import aiohttp

API_KEY = "fc-072741aa600f4082aa21c2c8a773dfed"

async def test_simple_request():
    """Test the simplest possible request."""
    print("🔍 Testing simple request...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Try the exact payload from the documentation
    payload = {
        "url": "https://httpbin.org/html",
        "formats": ["markdown", "html"]
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status == 200:
                result = await response.json()
                print("✅ Success!")
                print(f"Response: {json.dumps(result, indent=2)}")
            else:
                error_text = await response.text()
                print(f"❌ Error: {error_text}")
                
                # Try to parse as JSON
                try:
                    error_json = await response.json()
                    print(f"Error JSON: {json.dumps(error_json, indent=2)}")
                except:
                    pass

async def test_documentation_example():
    """Test the exact example from the documentation."""
    print("\n📖 Testing documentation example...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Use the exact example from the docs
    payload = {
        "url": "firecrawl.dev",
        "formats": ["markdown", "html"]
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("✅ Success!")
                data = result.get("data", {})
                print(f"Markdown length: {len(data.get('markdown', ''))} chars")
                print(f"Title: {data.get('metadata', {}).get('title', 'N/A')}")
            else:
                error_text = await response.text()
                print(f"❌ Error: {error_text}")

async def test_with_actions():
    """Test with actions as shown in documentation."""
    print("\n🎭 Testing with actions...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": "https://httpbin.org/forms/post",
        "formats": ["markdown", "html"],
        "actions": [
            {"type": "wait", "milliseconds": 2000},
            {"type": "scrape"}
        ]
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("✅ Success!")
                data = result.get("data", {})
                print(f"Markdown length: {len(data.get('markdown', ''))} chars")
            else:
                error_text = await response.text()
                print(f"❌ Error: {error_text}")

async def main():
    """Run all debug tests."""
    print("🚀 Firecrawl API Debug Tests")
    print("=" * 40)
    
    await test_simple_request()
    await test_documentation_example()
    await test_with_actions()

if __name__ == "__main__":
    asyncio.run(main()) 