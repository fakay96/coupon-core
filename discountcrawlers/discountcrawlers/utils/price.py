"""Utilities for parsing price and discount strings.

This module provides functions to parse Euro-formatted prices and percent discounts.
"""

import re
from typing import Optional

EURO_PATTERN: re.Pattern = re.compile(r"[€\u20AC]")
DECIMAL_COMMA_PATTERN: re.Pattern = re.compile(r",")

def parse_euro_price(raw: Optional[str]) -> Optional[float]:
    """Parse a Euro-formatted price string into a float.

    Args:
        raw: a string like "€ 12,34" or None.

    Returns:
        A float price, or None if parsing fails.
    """
    if raw is None:
        return None
    cleaned = EURO_PATTERN.sub("", raw).strip()
    cleaned = DECIMAL_COMMA_PATTERN.sub(".", cleaned)
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned.replace(" ", ""))
    except ValueError:
        return None

def parse_discount_percentage(raw: Optional[str]) -> Optional[int]:
    """Parse a discount percentage string into an integer.

    Args:
        raw: a string like "-20%" or None.

    Returns:
        An integer percent, or None if parsing fails.
    """
    if not raw:
        return None
    cleaned = raw.replace("%", "").replace("-", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None
