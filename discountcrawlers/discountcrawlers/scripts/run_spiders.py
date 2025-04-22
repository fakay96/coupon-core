"""Script to run all discount crawler spiders."""

import os
import sys
import logging
import asyncio
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from twisted.internet import asyncioreactor
from playwright.sync_api import sync_playwright

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler.log')
    ]
)

LOGGER = logging.getLogger(__name__)


def ensure_playwright_browsers():
    """Ensure Playwright browsers are installed."""
    try:
        with sync_playwright() as p:
            # This will trigger browser installation if needed
            browser = p.chromium.launch()
            browser.close()
        LOGGER.info("Playwright browsers verified")
    except Exception as e:
        LOGGER.error(f"Error verifying Playwright browsers: {e}")
        sys.exit(1)


def run_spiders():
    """Run all discount crawler spiders."""
    try:
        # Ensure Playwright browsers are installed
        ensure_playwright_browsers()
        
        # Install the asyncio reactor
        asyncioreactor.install(asyncio.new_event_loop())
        
        # Get Scrapy settings
        settings = get_project_settings()
        
        # Update settings for Playwright
        settings.set('TWISTED_REACTOR', 'twisted.internet.asyncioreactor.AsyncioSelectorReactor')
        settings.set('DOWNLOAD_HANDLERS', {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        })
        settings.set('CONCURRENT_REQUESTS', 1)
        settings.set('CONCURRENT_REQUESTS_PER_DOMAIN', 1)
        settings.set('DOWNLOAD_DELAY', 2)
        settings.set('RANDOMIZE_DOWNLOAD_DELAY', True)
        settings.set('PLAYWRIGHT_LAUNCH_OPTIONS', {
            'headless': True,
            'timeout': 30 * 1000,  # 30 seconds
            'args': [
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
            ]
        })
        settings.set('PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT', 30000)
        settings.set('PLAYWRIGHT_MAX_CONTEXTS', 1)
        settings.set('PLAYWRIGHT_MAX_PAGES_PER_CONTEXT', 1)
        
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Import only existing spiders
        from discountcrawlers.spiders.mueller_spider import MuellerSpider
        from discountcrawlers.spiders.zalando_spider import ZalandoSpider
        
        # Add spiders to process
        process.crawl(MuellerSpider)
        process.crawl(ZalandoSpider)
        
        # Start the crawler
        process.start()
        
        LOGGER.info("All spiders completed successfully")
        
    except Exception as e:
        LOGGER.error(f"Error running spiders: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_spiders() 