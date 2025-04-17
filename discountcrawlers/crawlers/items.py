"""discountscraper.items
====================================
Typed representations for discount products.

We keep two complementary classes:

* **DiscountItem** – a regular ``scrapy.Item`` that Scrapy’s engine and
  exporters understand.

* **DiscountData** – a frozen dataclass used in the rest of the
  code‑base for stronger typing and nicer tooling support.

Convert freely between the two with :pymeth:`DiscountData.to_item`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import scrapy


# ────────────────────────────────
#  Scrapy Item
# ────────────────────────────────
class DiscountItem(scrapy.Item):
    """Container passed to Scrapy pipelines/exporters."""

    url: scrapy.Field = scrapy.Field()
    brand: scrapy.Field = scrapy.Field()
    name: scrapy.Field = scrapy.Field()
    sale_price: scrapy.Field = scrapy.Field()
    original_price: scrapy.Field = scrapy.Field()
    discount_percentage: scrapy.Field = scrapy.Field()
    price_per_unit: scrapy.Field = scrapy.Field()
    stock_info: scrapy.Field = scrapy.Field()
    category: scrapy.Field = scrapy.Field()
    timestamp: scrapy.Field = scrapy.Field()

    # Helpers ----------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a plain‑Python ``dict`` copy of this item."""
        return dict(self)


# ────────────────────────────────
#  Dataclass model
# ────────────────────────────────
@dataclass(slots=True, frozen=False)
class DiscountData:
    """Strongly‑typed discount product model."""

    url: str
    brand: Optional[str] = None
    name: Optional[str] = None
    sale_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[int] = None  # without the «%» sign
    price_per_unit: Optional[str] = None
    stock_info: Optional[str] = None
    category: Optional[str] = None
    timestamp: Optional[str] = None  # ISO‑8601

    # Conversions ------------------------------------------------------
    def to_item(self) -> DiscountItem:
        """Convert into a :class:`DiscountItem` ready for Scrapy."""
        item = DiscountItem()
        item.update(asdict(self))
        return item

    def to_json(self, *, ensure_ascii: bool = False, **kw) -> str:
        """Dump to JSON string (handy for cache/debug)."""
        return json.dumps(asdict(self), ensure_ascii=ensure_ascii, **kw)
