"""Storage service for discount items.

This module provides a StorageService class for storing and retrieving discount items
using Redis as a backend.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.items import DiscountItem

class StorageService:
    """Service for storing and retrieving discount items."""

    def __init__(self, redis_utils: RedisUtils):
        """Initialize StorageService.
        
        Args:
            redis_utils: Instance of RedisUtils for Redis operations
        """
        self.redis_utils = redis_utils

    async def store_item(self, item: DiscountItem) -> bool:
        """Store a single discount item.
        
        Args:
            item: DiscountItem to store
            
        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Store item data in Redis
            item_data = {
                "title": item["title"],
                "price": item["price"],
                "original_price": item["original_price"],
                "url": item["url"],
                "store_name": item["store_name"],
                "valid_from": item["valid_from"].isoformat(),
                "valid_until": item["valid_until"].isoformat()
            }
            
            # Use URL as key
            key = f"item:{item['url']}"
            self.redis_utils.client.set(key, json.dumps(item_data))
            
            return True
        except Exception as e:
            return False

    async def store_items(self, items: List[DiscountItem]) -> bool:
        """Store multiple discount items.
        
        Args:
            items: List of DiscountItems to store
            
        Returns:
            True if all items were stored successfully, False otherwise
        """
        try:
            for item in items:
                success = await self.store_item(item)
                if not success:
                    return False
            return True
        except Exception as e:
            return False

    async def get_item(self, url: str) -> Optional[DiscountItem]:
        """Retrieve a single discount item by URL.
        
        Args:
            url: URL of the item to retrieve
            
        Returns:
            DiscountItem if found, None otherwise
        """
        try:
            # Get item data from Redis
            key = f"item:{url}"
            data = self.redis_utils.client.get(key)
            
            if not data:
                return None
                
            # Parse JSON data
            item_data = json.loads(data)
            
            # Create DiscountItem instance
            item = DiscountItem()
            item["title"] = item_data["title"]
            item["price"] = item_data["price"]
            item["original_price"] = item_data["original_price"]
            item["url"] = item_data["url"]
            item["store_name"] = item_data["store_name"]
            item["valid_from"] = datetime.fromisoformat(item_data["valid_from"])
            item["valid_until"] = datetime.fromisoformat(item_data["valid_until"])
            return item
        except Exception as e:
            return None

    async def get_items(self, urls: List[str]) -> List[DiscountItem]:
        """Retrieve multiple discount items by URLs.
        
        Args:
            urls: List of URLs to retrieve
            
        Returns:
            List of found DiscountItems
        """
        items = []
        for url in urls:
            item = await self.get_item(url)
            if item:
                items.append(item)
        return items

    async def update_item(self, item: DiscountItem) -> bool:
        """Update an existing discount item.
        
        Args:
            item: Updated DiscountItem
            
        Returns:
            True if update was successful, False otherwise
        """
        return await self.store_item(item)

    async def delete_item(self, url: str) -> bool:
        """Delete a discount item by URL.
        
        Args:
            url: URL of the item to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            key = f"item:{url}"
            self.redis_utils.client.delete(key)
            return True
        except Exception as e:
            return False

    async def list_items(self) -> List[DiscountItem]:
        """List all stored discount items.
        
        Returns:
            List of all stored DiscountItems
        """
        try:
            # Get all item keys
            keys = self.redis_utils.client.keys("item:*")
            
            items = []
            for key in keys:
                url = key.replace("item:", "")
                item = await self.get_item(url)
                if item:
                    items.append(item)
                    
            return items
        except Exception as e:
            return [] 