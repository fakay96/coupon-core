#!/usr/bin/env python3
"""
Debug script to compare working vs integration requests
=====================================================
"""

import asyncio
import json
import aiohttp

API_KEY = "fc-072741aa600f4082aa21c2c8a773dfed"

async def test_working_request():
    """Test the working request structure."""
    print("🔍 Testing working request structure...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Working payload from debug script
    payload = {
        "url": "https://httpbin.org/html",
        "formats": ["markdown", "html"]
    }
    
    print(f"Working payload: {json.dumps(payload, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("✅ Working request successful!")
                return True
            else:
                error_text = await response.text()
                print(f"❌ Working request failed: {error_text}")
                return False

async def test_integration_request():
    """Test the integration request structure."""
    print("\n🔧 Testing integration request structure...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Integration payload (what the integration sends)
    payload = {
        "url": "https://httpbin.org/html",
        "formats": ["markdown", "html"],
        "onlyMainContent": True  # This might be the issue
    }
    
    print(f"Integration payload: {json.dumps(payload, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("✅ Integration request successful!")
                return True
            else:
                error_text = await response.text()
                print(f"❌ Integration request failed: {error_text}")
                return False

async def test_with_actions():
    """Test with actions that the integration uses."""
    print("\n🎭 Testing with actions...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Payload with actions (what the integration sends)
    payload = {
        "url": "https://httpbin.org/html",
        "formats": ["markdown", "html"],
        "actions": [
            {"type": "wait", "milliseconds": 2000},
            {"type": "scrape"}
        ]
    }
    
    print(f"Actions payload: {json.dumps(payload, indent=2)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("✅ Actions request successful!")
                return True
            else:
                error_text = await response.text()
                print(f"❌ Actions request failed: {error_text}")
                return False

async def main():
    """Run all debug tests."""
    print("🚀 Firecrawl Request Structure Debug")
    print("=" * 40)
    
    await test_working_request()
    await test_integration_request()
    await test_with_actions()

if __name__ == "__main__":
    asyncio.run(main()) 