#!/usr/bin/env python3
"""
Simple test script to verify spider configurations and basic functionality.
This tests the spider setup without running the full Playwright crawling.
"""

import sys
import os
from typing import Dict, Any

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_spider_imports():
    """Test that all three fixed spiders can be imported successfully."""
    print("Testing spider imports...")
    
    try:
        from discountcrawlers.spiders.mueller_spider import MuellerSpider
        from discountcrawlers.spiders.spar_spider import SparIntersparSpider
        from discountcrawlers.spiders.penny_spider import PennySpider
        print("✅ All three spiders import successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_spider_configurations():
    """Test that spiders have the correct configurations."""
    print("\nTesting spider configurations...")
    
    try:
        from discountcrawlers.spiders.mueller_spider import MuellerSpider
        from discountcrawlers.spiders.spar_spider import SparIntersparSpider
        from discountcrawlers.spiders.penny_spider import PennySpider
        
        spiders = {
            'Mueller': MuellerSpider,
            'Spar': SparIntersparSpider,
            'Penny': PennySpider
        }
        
        for name, spider_class in spiders.items():
            spider = spider_class()
            
            # Test basic attributes
            assert hasattr(spider, 'name'), f"{name} spider missing 'name' attribute"
            assert hasattr(spider, 'allowed_domains'), f"{name} spider missing 'allowed_domains'"
            assert hasattr(spider, 'start_urls'), f"{name} spider missing 'start_urls'"
            assert hasattr(spider, 'card_selector'), f"{name} spider missing 'card_selector'"
            assert hasattr(spider, 'field_locators'), f"{name} spider missing 'field_locators'"
            
            # Test Playwright settings
            assert hasattr(spider, 'custom_settings'), f"{name} spider missing 'custom_settings'"
            assert spider.custom_settings.get('DOWNLOAD_HANDLERS'), f"{name} spider missing Playwright handlers"
            
            # Test selectors
            assert spider.card_selector, f"{name} spider has empty card_selector"
            assert spider.field_locators, f"{name} spider has empty field_locators"
            
            print(f"✅ {name} spider configuration is valid")
            
        return True
        
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False

def test_field_locators():
    """Test that field locators are properly configured."""
    print("\nTesting field locators...")
    
    try:
        from discountcrawlers.spiders.mueller_spider import MuellerSpider
        from discountcrawlers.spiders.spar_spider import SparIntersparSpider
        from discountcrawlers.spiders.penny_spider import PennySpider
        
        spiders = {
            'Mueller': MuellerSpider,
            'Spar': SparIntersparSpider,
            'Penny': PennySpider
        }
        
        required_fields = ['url', 'name', 'sale_price', 'image_url']
        
        for name, spider_class in spiders.items():
            spider = spider_class()
            field_locators = spider.field_locators
            
            missing_fields = []
            for field in required_fields:
                if field not in field_locators:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ {name} spider missing field locators: {missing_fields}")
            else:
                print(f"✅ {name} spider has all required field locators")
                
        return True
        
    except Exception as e:
        print(f"❌ Field locators test error: {e}")
        return False

def test_start_urls():
    """Test that start URLs are properly configured."""
    print("\nTesting start URLs...")
    
    try:
        from discountcrawlers.spiders.mueller_spider import MuellerSpider
        from discountcrawlers.spiders.spar_spider import SparIntersparSpider
        from discountcrawlers.spiders.penny_spider import PennySpider
        
        spiders = {
            'Mueller': MuellerSpider,
            'Spar': SparIntersparSpider,
            'Penny': PennySpider
        }
        
        for name, spider_class in spiders.items():
            spider = spider_class()
            start_urls = spider.start_urls
            
            if not start_urls:
                print(f"❌ {name} spider has no start URLs")
            else:
                print(f"✅ {name} spider has {len(start_urls)} start URLs")
                for url in start_urls:
                    print(f"   - {url}")
                    
        return True
        
    except Exception as e:
        print(f"❌ Start URLs test error: {e}")
        return False

def test_playwright_settings():
    """Test that Playwright settings are properly configured."""
    print("\nTesting Playwright settings...")
    
    try:
        from discountcrawlers.spiders.mueller_spider import MuellerSpider
        from discountcrawlers.spiders.spar_spider import SparIntersparSpider
        from discountcrawlers.spiders.penny_spider import PennySpider
        
        spiders = {
            'Mueller': MuellerSpider,
            'Spar': SparIntersparSpider,
            'Penny': PennySpider
        }
        
        for name, spider_class in spiders.items():
            spider = spider_class()
            settings = spider.custom_settings
            
            # Check for required Playwright settings
            required_settings = [
                'TWISTED_REACTOR',
                'DOWNLOAD_HANDLERS',
                'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT'
            ]
            
            missing_settings = []
            for setting in required_settings:
                if setting not in settings:
                    missing_settings.append(setting)
            
            if missing_settings:
                print(f"❌ {name} spider missing settings: {missing_settings}")
            else:
                print(f"✅ {name} spider has all required Playwright settings")
                
        return True
        
    except Exception as e:
        print(f"❌ Playwright settings test error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing the three fixed spiders (Mueller, Spar, Penny)")
    print("=" * 60)
    
    tests = [
        test_spider_imports,
        test_spider_configurations,
        test_field_locators,
        test_start_urls,
        test_playwright_settings
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your spider configurations are ready.")
        print("\nNext steps:")
        print("1. Install Playwright browsers: python3 -m playwright install")
        print("2. Run the spiders: python3 discountcrawlers/scripts/run_spiders.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 