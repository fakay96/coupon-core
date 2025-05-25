"""Scrapy settings for discountcrawlers project."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Scrapy settings
BOT_NAME = 'discountcrawlers'

SPIDER_MODULES = ['discountcrawlers.spiders']
NEWSPIDER_MODULE = 'discountcrawlers.spiders'

# Crawl responsibly by identifying yourself
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

   

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
    'discountcrawlers.middlewares.headers.browser.FakeBrowserHeaderMiddleware': 400,
}


# Configure item pipelines
ITEM_PIPELINES = {
    'discountcrawlers.pipelines.pipelines.DiscountPipeline': 300,
    'discountcrawlers.pipelines.pipelines.DealsAndEmbedPipeline': 400,
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Redis settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Logging settings
LOG_LEVEL = 'INFO'
LOG_FILE = 'crawler.log'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# Splash settings (if using)
SPLASH_URL = os.getenv('SPLASH_URL', 'http://localhost:8050')
DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'
HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'

# Playwright settings
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
# PLAYWRIGHT_BROWSER_TYPE = "chromium"
# PLAYWRIGHT_LAUNCH_OPTIONS = {
#     "headless": True,
#     "timeout": 20 * 1000,  # 20 seconds
# }
# PLAYWRIGHT_CONTEXT_ARGS = {
#     "ignore_https_errors": True,
# }
# PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30 * 1000  # 30 seconds

AWS_S3_ENDPOINT_URL = os.getenv('DO_SPACES_ENDPOINT_URL', 'https://nyc3.digitaloceanspaces.com')
AWS_ACCESS_KEY_ID = os.getenv('DO_SPACES_ACCESS_KEY_ID', 'DO00300000000000000000000')
AWS_SECRET_ACCESS_KEY = os.getenv('DO_SPACES_SECRET_ACCESS_KEY', 'DO00300000000000000000000')
AWS_STORAGE_BUCKET_NAME = os.getenv('DO_SPACES_BUCKET_NAME', 'discountcrawlers')

BASE_URL=os.getenv("BASE_URL")
DISCOUNT_IMPORT_API_ENDPOINT = f'{BASE_URL}/geodiscounts/v1/discounts/publish/'
DISCOUNT_IMPORT_API_KEY = os.getenv("DISHPAL_EMAIL_PASSWORD")
DISCOUNT_IMPORT_API_TIMEOUT = 30  # seconds