"""discountscraper.utils.price
===================================
Helper functions for dealing with price and discount strings.
"""
from __future__ import annotations

import re
from typing import Optional


_EURO_RE = re.compile(r"[€\u20AC]")  # Matches the Euro sign.
_DECIMAL_COMMA = re.compile(r",")


def parse_euro_price(raw: str | None) -> Optional[float]:
    """Parse a price string like "€ 12,34" into a ``float``.

    Returns ``None`` if *raw* is *falsy* or cannot be converted.
    """
    if not raw:
        return None

    try:
        cleaned = _EURO_RE.sub("", raw)
        cleaned = cleaned.replace("\xa0", "").strip()
        # Replace decimal comma with dot for Python ``float``.
        cleaned = _DECIMAL_COMMA.sub(".", cleaned)
        # Remove any lingering whitespace.
        cleaned = cleaned.strip()
        return float(cleaned)
    except ValueError:
        return None


def parse_discount_percentage(raw: str | None) -> Optional[int]:
    """Turn a string like "-20%" into an ``int`` ``20``.

    Returns ``None`` when conversion fails.
    """
    if not raw:
        return None

    cleaned = raw.replace("%", "").replace("-", "").strip()

    try:
        return int(cleaned)
    except ValueError:
        return None
