"""Utility sub‑package for *discountscraper*.

Anything that is **not** a Scrapy component (spider, pipeline, extension)
belongs in this namespace. Keeping business logic separate from Scrapy’s
classes makes it trivial to reuse / unit‑test the functionality in other
contexts.
"""
__all__ = ["price", "splash"]
