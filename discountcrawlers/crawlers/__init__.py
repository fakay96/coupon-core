"""discountscraper
====================

A **Scrapy** project for harvesting product discounts from various e‑commerce
sites. The code has been refactored to embrace modern Python:

* **Type hints** everywhere (requires Python 3.9+).
* Clear *Separation of Concerns* – business utilities live under
  :pymod:`discountscraper.utils`.
* Thorough **Google‑style docstrings** to make the public API self‑explanatory.
* Ready for **asyncio** – although Scrapy is still based on Twisted, all pure
  Python helper functions are fully «awaitable» and can be reused in
  asynchronous contexts.
"""
__all__ = ["items", "pipelines", "utils"]
