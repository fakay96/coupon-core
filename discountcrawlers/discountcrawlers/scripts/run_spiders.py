# filename: discountcrawlers/scripts/run_spiders.py

import os
import sys
import logging
import shutil
import argparse
# import asyncio # No longer needed for this script if not using Playwright directly here
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
# from twisted.internet import asyncioreactor # Not needed for Splash
# from playwright.sync_api import sync_playwright # Not needed for Splash

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Configure logging
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

def setup_logging(log_level: str = 'INFO'):
    """Configure logging with specified level.
    
    Args:
        log_level: The logging level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
        
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, 'crawler.log'))
        ]
    )

LOGGER = logging.getLogger(__name__)

# Removed ensure_playwright_browsers function as it's not needed for Splash

def cleanup_scrapy_dirs():
    """Remove any .scrapy directories that might have been created."""
    scrapy_dir = os.path.join(project_root, '.scrapy')
    if os.path.exists(scrapy_dir):
        try:
            shutil.rmtree(scrapy_dir)
            LOGGER.info("Cleaned up .scrapy directory")
        except Exception as e:
            LOGGER.warning(f"Failed to clean up .scrapy directory: {e}")

def run_spiders():
    """Run all discount crawler spiders."""
    try:
        # Clean up any existing .scrapy directory
        cleanup_scrapy_dirs()

        # Get Scrapy settings (These should be configured for Splash in settings.py)
        settings = get_project_settings()

        # Ensure settings are loaded correctly
        if not settings:
            LOGGER.error("Could not load Scrapy project settings. Check settings.py path and content.")
            sys.exit(1)
        LOGGER.info("Loaded Scrapy settings.")
        # Optional: Log specific settings to verify
        # LOGGER.info(f"SPLASH_URL: {settings.get('SPLASH_URL')}")
        # LOGGER.info(f"DOWNLOADER_MIDDLEWARES: {settings.get('DOWNLOADER_MIDDLEWARES')}")

        # Create crawler process with custom settings
        process = CrawlerProcess(settings)

        # Import spiders (make sure paths are correct)
        try:
            from discountcrawlers.spiders.mueller_spider import MuellerSpider
            from discountcrawlers.spiders.zalando_spider import ZalandoSpider # Keep import if you might run it later
            from discountcrawlers.spiders.penny_spider import PennySpider
            LOGGER.info("Successfully imported spiders.")
        except ImportError as e:
            LOGGER.error(f"Failed to import spiders. Check sys.path and file locations: {e}")
            sys.exit(1)

        # Add spiders to process
        # Decide which spiders to run here:
        LOGGER.info("Adding spiders to crawl process...")
        # process.crawl(MuellerSpider) # Uncomment if you want to run Mueller
        process.crawl(PennySpider)   # *** UNCOMMENTED PENNY SPIDER ***
       # process.crawl(ZalandoSpider) # Keep commented if not running

        LOGGER.info("Starting crawler process...")
        # Start the crawler (this blocks until done)
        process.start()

        LOGGER.info("Crawler process finished.")

    except Exception as e:
        # Log the exception traceback for more details
        LOGGER.error(f"Unhandled error running spiders: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up .scrapy directory after running
        cleanup_scrapy_dirs()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run discount crawler spiders')
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.log_level)
    LOGGER.info(f"Running spiders script with log level: {args.log_level}")
    run_spiders()
    LOGGER.info("Spiders script finished.")