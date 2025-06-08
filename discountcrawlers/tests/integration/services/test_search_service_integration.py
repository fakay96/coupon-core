import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
"""Integration tests for the search service."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.items import DiscountItem
from discountcrawlers.services.search_service import SearchService
from discountcrawlers.services.storage_service import StorageService

@pytest.fixture
def redis_utils():
    """Initialize RedisUtils instance."""
    return RedisUtils()

@pytest.fixture
def storage_service(redis_utils):
    """Initialize StorageService instance."""
    return StorageService(redis_utils)

@pytest.fixture
def search_service(redis_utils, storage_service):
    """Initialize SearchService instance."""
    return SearchService(redis_utils, storage_service)

@pytest.fixture
def sample_items():
    """Create sample DiscountItems for testing."""
    items = []
    for i in range(10):
        item = DiscountItem()
        item["title"] = f"Test Item {i}"
        item["price"] = 99.99 + (i * 10)
        item["original_price"] = 149.99 + (i * 10)
        item["url"] = f"https://test.com/item{i}"
        item["store_name"] = "TestStore" if i % 2 == 0 else "OtherStore"
        item["valid_from"] = datetime.now()
        item["valid_until"] = datetime.now() + timedelta(days=7)
        items.append(item)
    return items

@pytest.mark.asyncio
async def test_search_service_initialization(search_service):
    """Test that the search service initializes correctly."""
    assert search_service is not None
    assert search_service.redis_utils is not None
    assert search_service.storage_service is not None

@pytest.mark.asyncio
async def test_basic_search(search_service, storage_service, sample_items):
    """Test basic search functionality."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Perform basic search
    results = await search_service.search("Test Item")
    assert len(results) > 0
    assert all("Test Item" in item["title"] for item in results)

@pytest.mark.asyncio
async def test_price_range_search(search_service, storage_service, sample_items):
    """Test search with price range filter."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Search with price range
    min_price = 120.0
    max_price = 180.0
    results = await search_service.search_by_price_range(min_price, max_price)
    
    assert len(results) > 0
    assert all(min_price <= item["price"] <= max_price for item in results)

@pytest.mark.asyncio
async def test_store_search(search_service, storage_service, sample_items):
    """Test search by store."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Search by store
    store = "TestStore"
    results = await search_service.search_by_store(store)
    
    assert len(results) > 0
    assert all(item["store_name"] == store for item in results)

@pytest.mark.asyncio
async def test_combined_search(search_service, storage_service, sample_items):
    """Test search with multiple criteria."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Search with multiple criteria
    results = await search_service.search(
        query="Test Item",
        store="TestStore",
        min_price=100.0,
        max_price=150.0
    )
    
    assert len(results) > 0
    assert all(
        "Test Item" in item["title"]
        and item["store_name"] == "TestStore"
        and 100.0 <= item["price"] <= 150.0
        for item in results
    )

@pytest.mark.asyncio
async def test_search_pagination(search_service, storage_service, sample_items):
    """Test search results pagination."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Test pagination
    page_size = 3
    page1 = await search_service.search("Test Item", page=1, page_size=page_size)
    page2 = await search_service.search("Test Item", page=2, page_size=page_size)
    
    assert len(page1) == page_size
    assert len(page2) <= page_size
    assert set(item["url"] for item in page1).isdisjoint(set(item["url"] for item in page2))

@pytest.mark.asyncio
async def test_search_sorting(search_service, storage_service, sample_items):
    """Test search results sorting."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Test sorting by price ascending
    results_asc = await search_service.search("Test Item", sort_by="price", sort_order="asc")
    assert len(results_asc) > 0
    assert all(results_asc[i]["price"] <= results_asc[i+1]["price"] for i in range(len(results_asc)-1))

    # Test sorting by price descending
    results_desc = await search_service.search("Test Item", sort_by="price", sort_order="desc")
    assert len(results_desc) > 0
    assert all(results_desc[i]["price"] >= results_desc[i+1]["price"] for i in range(len(results_desc)-1))

@pytest.mark.asyncio
async def test_search_error_handling(search_service):
    """Test error handling in search operations."""
    # Test with invalid price range
    results = await search_service.search_by_price_range(-100, 50)
    assert len(results) == 0

    # Test with non-existent store
    results = await search_service.search_by_store("NonExistentStore")
    assert len(results) == 0

    # Test with invalid pagination
    results = await search_service.search("Test Item", page=0, page_size=-1)
    assert len(results) == 0

@pytest.mark.asyncio
async def test_concurrent_searches(search_service, storage_service, sample_items):
    """Test concurrent search operations."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Perform concurrent searches
    search_tasks = [
        search_service.search("Test Item"),
        search_service.search_by_store("TestStore"),
        search_service.search_by_price_range(100, 200)
    ]
    
    results = await asyncio.gather(*search_tasks)
    assert all(len(result) > 0 for result in results)

@pytest.mark.asyncio
async def test_search_cache(search_service, storage_service, sample_items):
    """Test search result caching."""
    # Store sample items
    for item in sample_items:
        await storage_service.store_item(item)

    # Perform initial search
    query = "Test Item"
    first_results = await search_service.search(query)
    
    # Perform same search again (should use cache)
    second_results = await search_service.search(query)
    
    assert len(first_results) == len(second_results)
    assert all(
        first["url"] == second["url"]
        for first, second in zip(first_results, second_results)
    ) 