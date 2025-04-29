"""Integration tests for the storage service with Redis integration."""
import asyncio
import pytest
from datetime import datetime, timedelta
from typing import AsyncGenerator, List

from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.services.storage_service import StorageService
from discountcrawlers.models.discount_item import DiscountItem

@pytest.fixture
async def redis_utils() -> AsyncGenerator[RedisUtils, None]:
    """Initialize RedisUtils for testing."""
    redis = RedisUtils()
    await redis.initialize()
    yield redis
    await redis.clear_all()
    await redis.close()

@pytest.fixture
async def storage_service(redis_utils: RedisUtils) -> AsyncGenerator[StorageService, None]:
    """Initialize StorageService with RedisUtils for testing."""
    service = StorageService(redis_utils=redis_utils)
    yield service
    await service.cleanup()

@pytest.fixture
def sample_item() -> DiscountItem:
    """Create a sample DiscountItem for testing."""
    return DiscountItem(
        title="Test Item",
        price=9.99,
        original_price=19.99,
        url="https://test.com/item",
        store="TestStore",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )

@pytest.mark.asyncio
async def test_storage_service_initialization(storage_service: StorageService):
    """Test storage service initialization."""
    assert storage_service is not None
    assert storage_service.redis_utils is not None

@pytest.mark.asyncio
async def test_store_and_retrieve_item(storage_service: StorageService, sample_item: DiscountItem):
    """Test storing and retrieving a single item."""
    # Store item
    await storage_service.store_item(sample_item)
    
    # Retrieve item
    retrieved_item = await storage_service.get_item(sample_item.id)
    assert retrieved_item is not None
    assert retrieved_item.title == sample_item.title
    assert retrieved_item.price == sample_item.price

@pytest.mark.asyncio
async def test_batch_store_and_retrieve(storage_service: StorageService, sample_item: DiscountItem):
    """Test batch operations for storing and retrieving items."""
    items = [
        sample_item,
        DiscountItem(
            title="Test Item 2",
            price=14.99,
            original_price=29.99,
            url="https://test.com/item2",
            store="TestStore",
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=7)
        )
    ]
    
    # Store items in batch
    await storage_service.store_items(items)
    
    # Retrieve all items
    stored_items = await storage_service.get_items([item.id for item in items])
    assert len(stored_items) == len(items)
    assert all(isinstance(item, DiscountItem) for item in stored_items)

@pytest.mark.asyncio
async def test_update_item(storage_service: StorageService, sample_item: DiscountItem):
    """Test updating an existing item."""
    # Store initial item
    await storage_service.store_item(sample_item)
    
    # Update item
    updated_price = 7.99
    sample_item.price = updated_price
    await storage_service.update_item(sample_item)
    
    # Verify update
    updated_item = await storage_service.get_item(sample_item.id)
    assert updated_item is not None
    assert updated_item.price == updated_price

@pytest.mark.asyncio
async def test_delete_item(storage_service: StorageService, sample_item: DiscountItem):
    """Test deleting an item."""
    # Store item
    await storage_service.store_item(sample_item)
    
    # Delete item
    await storage_service.delete_item(sample_item.id)
    
    # Verify deletion
    deleted_item = await storage_service.get_item(sample_item.id)
    assert deleted_item is None

@pytest.mark.asyncio
async def test_list_items(storage_service: StorageService, sample_item: DiscountItem):
    """Test listing all items."""
    # Store multiple items
    items = [
        sample_item,
        DiscountItem(
            title="Test Item 2",
            price=14.99,
            original_price=29.99,
            url="https://test.com/item2",
            store="TestStore",
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=7)
        )
    ]
    await storage_service.store_items(items)
    
    # List all items
    all_items = await storage_service.list_items()
    assert len(all_items) >= len(items)

@pytest.mark.asyncio
async def test_error_handling(storage_service: StorageService):
    """Test error handling for invalid operations."""
    # Test retrieving non-existent item
    non_existent_id = "non_existent_id"
    item = await storage_service.get_item(non_existent_id)
    assert item is None
    
    # Test updating non-existent item
    with pytest.raises(Exception):
        await storage_service.update_item(DiscountItem(
            id=non_existent_id,
            title="Non-existent",
            price=0.0,
            original_price=0.0,
            url="",
            store="",
            valid_from=datetime.now(),
            valid_to=datetime.now()
        ))

@pytest.mark.asyncio
async def test_concurrent_operations(storage_service: StorageService, sample_item: DiscountItem):
    """Test concurrent operations on the storage service."""
    # Create multiple items
    items = [
        DiscountItem(
            title=f"Test Item {i}",
            price=10.0 + i,
            original_price=20.0 + i,
            url=f"https://test.com/item{i}",
            store="TestStore",
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=7)
        )
        for i in range(5)
    ]
    
    # Concurrently store items
    await asyncio.gather(*(storage_service.store_item(item) for item in items))
    
    # Verify all items were stored
    stored_items = await storage_service.get_items([item.id for item in items])
    assert len(stored_items) == len(items) 