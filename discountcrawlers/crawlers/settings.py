"""Scrapy settings for the *crawlers* project.

Only the minimal settings required to run the refactored spiders are kept
here. For a full list see the Scrapy documentation:
https://docs.scrapy.org/en/latest/topics/settings.html
"""
from __future__ import annotations

BOT_NAME = "crawlers"

SPIDER_MODULES = ["crawlers.spiders"]
NEWSPIDER_MODULE = "crawlers.spiders"

# ------------------------------------------------------------------ #
# Splash integration                                                 #
# ------------------------------------------------------------------ #
SPLASH_URL = "http://localhost:8050"

DOWNLOADER_MIDDLEWARES = {
    "scrapy_splash.SplashCookiesMiddleware": 723,
    "scrapy_splash.SplashMiddleware": 725,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
}
DUPEFILTER_CLASS = "scrapy_splash.SplashAwareDupeFilter"
HTTPCACHE_STORAGE = "scrapy_splash.SplashAwareFSCacheStorage"

# ------------------------------------------------------------------ #
# Pipelines                                                          #
# ------------------------------------------------------------------ #
ITEM_PIPELINES = {
    "crawlers.pipelines.DiscountPipeline": 300,
    "crawlers.pipelines.DealsAndEmbedPipeline": 400,
}
# ITEM_PIPELINES = {
#     'discountscraper.pipelines.DiscountPipeline': 300,
#     'discountscraper.pipelines.DealsAndEmbedPipeline': 400,
#     # any downstream persistence/export pipelines at 500+
# }

# ------------------------------------------------------------------ #
# Output                                                             #
# ------------------------------------------------------------------ #
FEEDS = {
    "discounts.json": {
        "format": "json",
        "encoding": "utf-8",
        "overwrite": True,
        "indent": 2,
    },
}
