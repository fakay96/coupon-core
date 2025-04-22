"""Proxy health tracking functionality.

This module provides classes for tracking and reporting proxy health statistics.
"""

from __future__ import annotations
import logging
from typing import Any, Dict

LOGGER: logging.Logger = logging.getLogger(__name__)

class ProxyHealthTracker:
    """Track success/failure counts for proxy sources."""
    
    def __init__(self) -> None:
        """Initialize the health tracker."""
        self.health: Dict[str, Dict[str, int]] = {}

    def record(self, source: str, success: bool) -> None:
        """Record a success or failure for a given proxy source.
        
        Args:
            source: The proxy source identifier
            success: Whether the proxy request was successful
        """
        stats = self.health.setdefault(source, {"success": 0, "failure": 0})
        stats["success" if success else "failure"] += 1

    def report(self, spider: Any) -> None:
        """Log success rates for all proxy sources.
        
        Args:
            spider: The spider instance to log to
        """
        for source, stats in self.health.items():
            total = stats["success"] + stats["failure"]
            rate = (stats["success"] / total * 100) if total else 0.0
            spider.logger.info(
                "%s proxy health: %d/%d (%.2f%%)",
                source.title(),
                stats["success"],
                total,
                rate,
            ) 