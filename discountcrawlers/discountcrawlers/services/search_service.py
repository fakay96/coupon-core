"""Search service for discount items.

This module provides a SearchService class for searching and filtering discount items
using Redis as a backend.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.services.storage_service import StorageService
from discountcrawlers.items import DiscountItem

class SearchService:
    """Service for searching and filtering discount items."""

    def __init__(self, redis_utils: RedisUtils, storage_service: StorageService):
        """Initialize SearchService.
        
        Args:
            redis_utils: Instance of RedisUtils for Redis operations
            storage_service: Instance of StorageService for item storage
        """
        self.redis_utils = redis_utils
        self.storage_service = storage_service
        self._cache = {}

    async def search(
        self,
        query: str,
        store: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> List[DiscountItem]:
        """Search for discount items based on given criteria.
        
        Args:
            query: Search query string
            store: Optional store name to filter by
            min_price: Optional minimum price
            max_price: Optional maximum price
            page: Page number for pagination (1-based)
            page_size: Number of items per page
            sort_by: Field to sort by (e.g. "price", "title")
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            List of matching DiscountItem objects
        """
        # Check cache first
        cache_key = f"{query}:{store}:{min_price}:{max_price}:{page}:{page_size}:{sort_by}:{sort_order}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get all items from storage
        all_items = await self.storage_service.list_items()
        
        # Filter items
        filtered_items = []
        for item in all_items:
            if query.lower() not in item["title"].lower():
                continue
                
            if store and item["store_name"] != store:
                continue
                
            if min_price is not None and item["price"] < min_price:
                continue
                
            if max_price is not None and item["price"] > max_price:
                continue
                
            filtered_items.append(item)

        # Sort items
        if sort_by:
            reverse = sort_order.lower() == "desc"
            filtered_items.sort(
                key=lambda x: x[sort_by],
                reverse=reverse
            )

        # Paginate results
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = filtered_items[start_idx:end_idx]

        # Cache results
        self._cache[cache_key] = paginated_items
        
        return paginated_items

    async def search_by_price_range(
        self,
        min_price: float,
        max_price: float
    ) -> List[DiscountItem]:
        """Search for items within a price range.
        
        Args:
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            List of matching DiscountItem objects
        """
        return await self.search("", min_price=min_price, max_price=max_price)

    async def search_by_store(self, store: str) -> List[DiscountItem]:
        """Search for items from a specific store.
        
        Args:
            store: Store name to filter by
            
        Returns:
            List of matching DiscountItem objects
        """
        return await self.search("", store=store) 