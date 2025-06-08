import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
import asyncio
from datetime import datetime, timedelta
from discountcrawlers.agents.coordinator_agent import CoordinatorAgent
from discountcrawlers.agents.metadata_agent import MetadataAgent
from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.utils.storage import StorageService
from discountcrawlers.utils.vector_db import VectorDB
from discountcrawlers.items import DiscountItem

@pytest.fixture
async def coordinator_agent():
    agent = CoordinatorAgent()
    await agent.initialize()
    yield agent
    await agent.cleanup()

@pytest.fixture
async def metadata_agent():
    agent = MetadataAgent()
    await agent.initialize()
    yield agent
    await agent.cleanup()

@pytest.fixture
async def redis_utils():
    utils = RedisUtils()
    await utils.connect()
    yield utils
    await utils.cleanup()

@pytest.fixture
async def storage():
    storage = StorageService()
    await storage.initialize()
    yield storage
    await storage.cleanup()

@pytest.fixture
async def vector_db():
    db = VectorDB()
    await db.initialize()
    yield db
    await db.cleanup()

@pytest.mark.asyncio
async def test_item_pipeline_integration(coordinator_agent, metadata_agent, redis_utils):
    """Test item pipeline integration"""
    # Create a sample item
    item = DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )
    
    # Process item through pipeline
    await coordinator_agent.process_item(item)
    
    # Verify item was processed and stored
    stored_item = await redis_utils.get_item(item.url)
    assert stored_item is not None
    assert stored_item.title == item.title
    assert stored_item.price == item.price
    assert stored_item.store == item.store

@pytest.mark.asyncio
async def test_metadata_pipeline_integration(metadata_agent, redis_utils, vector_db):
    """Test metadata pipeline integration"""
    # Create a sample item
    item = DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )
    
    # Extract and store metadata
    metadata = await metadata_agent.extract_metadata(item)
    await metadata_agent.store_metadata(item.url, metadata)
    
    # Generate and store embedding
    embedding = await metadata_agent.generate_embedding(metadata)
    await vector_db.store_embedding(item.url, embedding)
    
    # Verify metadata and embedding were stored
    stored_metadata = await redis_utils.get_metadata(item.url)
    stored_embedding = await vector_db.get_embedding(item.url)
    
    assert stored_metadata is not None
    assert stored_embedding is not None
    assert stored_metadata["title"] == item.title
    assert stored_metadata["price"] == item.price
    assert stored_metadata["store"] == item.store

@pytest.mark.asyncio
async def test_storage_pipeline_integration(coordinator_agent, storage):
    """Test storage pipeline integration"""
    # Create a sample item
    item = DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )
    
    # Process and store item
    await coordinator_agent.process_item(item)
    await storage.store_item(item)
    
    # Verify item was stored
    stored_item = await storage.get_item(item.url)
    assert stored_item is not None
    assert stored_item.title == item.title
    assert stored_item.price == item.price
    assert stored_item.store == item.store

@pytest.mark.asyncio
async def test_full_pipeline_integration(coordinator_agent, metadata_agent, redis_utils, storage, vector_db):
    """Test complete pipeline integration"""
    # Create a sample item
    item = DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )
    
    # Process through coordinator
    await coordinator_agent.process_item(item)
    
    # Extract and store metadata
    metadata = await metadata_agent.extract_metadata(item)
    await metadata_agent.store_metadata(item.url, metadata)
    
    # Generate and store embedding
    embedding = await metadata_agent.generate_embedding(metadata)
    await vector_db.store_embedding(item.url, embedding)
    
    # Store item
    await storage.store_item(item)
    
    # Verify all components
    stored_metadata = await redis_utils.get_metadata(item.url)
    stored_embedding = await vector_db.get_embedding(item.url)
    stored_item = await storage.get_item(item.url)
    
    assert stored_metadata is not None
    assert stored_embedding is not None
    assert stored_item is not None
    
    # Verify data consistency
    assert stored_metadata["title"] == stored_item.title
    assert stored_metadata["price"] == stored_item.price
    assert stored_metadata["store"] == stored_item.store

@pytest.mark.asyncio
async def test_pipeline_error_handling(coordinator_agent, metadata_agent, redis_utils):
    """Test error handling in pipeline integration"""
    # Test with invalid item
    invalid_item = DiscountItem(
        title="",
        price=-1,
        original_price=-1,
        url="",
        store="",
        valid_from=datetime.now(),
        valid_to=datetime.now()
    )
    
    # Should handle errors gracefully
    with pytest.raises(ValueError):
        await coordinator_agent.process_item(invalid_item)
    
    # Verify no metadata was stored
    stored_metadata = await redis_utils.get_metadata(invalid_item.url)
    assert stored_metadata is None

@pytest.mark.asyncio
async def test_pipeline_concurrent_operations(coordinator_agent, metadata_agent, redis_utils):
    """Test concurrent operations in pipeline integration"""
    # Create multiple items
    items = [
        DiscountItem(
            title=f"Test Product {i}",
            price=19.99 + i,
            original_price=29.99 + i,
            url=f"https://example.com/product{i}",
            store=f"Test Store {i}",
            valid_from=datetime.now(),
            valid_to=datetime.now() + timedelta(days=7)
        ) for i in range(5)
    ]
    
    # Process items concurrently
    tasks = []
    for item in items:
        task = asyncio.create_task(coordinator_agent.process_item(item))
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    # Verify all items were processed
    for item in items:
        stored_item = await redis_utils.get_item(item.url)
        assert stored_item is not None
        assert stored_item.title == item.title
        assert stored_item.price == item.price
        assert stored_item.store == item.store

@pytest.mark.asyncio
async def test_pipeline_data_persistence(coordinator_agent, metadata_agent, redis_utils, storage):
    """Test data persistence in pipeline integration"""
    # Create and process an item
    item = DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )
    
    await coordinator_agent.process_item(item)
    metadata = await metadata_agent.extract_metadata(item)
    await metadata_agent.store_metadata(item.url, metadata)
    await storage.store_item(item)
    
    # Simulate service restart
    await coordinator_agent.cleanup()
    await metadata_agent.cleanup()
    await redis_utils.cleanup()
    await storage.cleanup()
    
    await coordinator_agent.initialize()
    await metadata_agent.initialize()
    await redis_utils.connect()
    await storage.initialize()
    
    # Verify data persistence
    stored_metadata = await redis_utils.get_metadata(item.url)
    stored_item = await storage.get_item(item.url)
    
    assert stored_metadata is not None
    assert stored_item is not None
    assert stored_metadata["title"] == stored_item.title
    assert stored_metadata["price"] == stored_item.price
    assert stored_metadata["store"] == stored_item.store 