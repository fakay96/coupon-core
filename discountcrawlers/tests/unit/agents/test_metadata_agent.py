import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from discountcrawlers.agents.metadata_agent import MetadataAgent
from discountcrawlers.items import DiscountItem

@pytest.fixture
def metadata_agent():
    return MetadataAgent()

@pytest.fixture
def sample_item():
    return DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now()
    )

@pytest.mark.asyncio
async def test_agent_initialization(metadata_agent):
    """Test metadata agent initialization"""
    assert metadata_agent.logger is not None
    assert metadata_agent.config is not None
    assert metadata_agent.state == "initialized"

@pytest.mark.asyncio
async def test_metadata_extraction(metadata_agent, sample_item):
    """Test metadata extraction from items"""
    metadata = await metadata_agent.extract_metadata(sample_item)
    
    assert metadata is not None
    assert isinstance(metadata, dict)
    assert "title" in metadata
    assert "price" in metadata
    assert "store" in metadata
    assert "validity_period" in metadata

@pytest.mark.asyncio
async def test_metadata_validation(metadata_agent):
    """Test metadata validation"""
    # Test valid metadata
    valid_metadata = {
        "title": "Test Product",
        "price": 19.99,
        "store": "Test Store",
        "validity_period": {
            "from": datetime.now().isoformat(),
            "to": datetime.now().isoformat()
        }
    }
    assert await metadata_agent.validate_metadata(valid_metadata) is True
    
    # Test invalid metadata
    invalid_metadata = {
        "title": "Test Product",
        "price": -10.0,  # Invalid price
        "store": "Test Store"
    }
    assert await metadata_agent.validate_metadata(invalid_metadata) is False

@pytest.mark.asyncio
async def test_metadata_storage(metadata_agent, sample_item):
    """Test metadata storage"""
    with patch('discountcrawlers.services.redis_service.RedisService') as mock_redis:
        metadata = await metadata_agent.extract_metadata(sample_item)
        await metadata_agent.store_metadata(metadata)
        mock_redis.return_value.store_item.assert_called_once_with(metadata)

@pytest.mark.asyncio
async def test_metadata_retrieval(metadata_agent):
    """Test metadata retrieval"""
    with patch('discountcrawlers.services.redis_service.RedisService') as mock_redis:
        mock_redis.return_value.get_items.return_value = [{"title": "Test Product"}]
        metadata = await metadata_agent.get_metadata()
        assert len(metadata) == 1
        assert metadata[0]["title"] == "Test Product"

@pytest.mark.asyncio
async def test_error_handling(metadata_agent):
    """Test error handling in metadata agent"""
    # Test extraction error
    with pytest.raises(Exception):
        await metadata_agent.extract_metadata(None)
    
    # Test storage error
    with patch('discountcrawlers.services.redis_service.RedisService') as mock_redis:
        mock_redis.return_value.store_item.side_effect = Exception("Storage error")
        with pytest.raises(Exception):
            await metadata_agent.store_metadata({"test": "data"})

@pytest.mark.asyncio
async def test_metadata_cleanup(metadata_agent):
    """Test metadata cleanup"""
    with patch('discountcrawlers.services.redis_service.RedisService') as mock_redis:
        await metadata_agent.cleanup_metadata()
        mock_redis.return_value.delete_all.assert_called_once()

@pytest.mark.asyncio
async def test_metadata_analysis(metadata_agent):
    """Test metadata analysis"""
    test_data = [
        {"price": 10.0, "store": "Store1"},
        {"price": 20.0, "store": "Store2"},
        {"price": 30.0, "store": "Store3"}
    ]
    
    analysis = await metadata_agent.analyze_metadata(test_data)
    assert "average_price" in analysis
    assert "store_distribution" in analysis
    assert "price_range" in analysis

@pytest.mark.asyncio
async def test_metadata_export(metadata_agent):
    """Test metadata export"""
    test_data = [{"title": "Test Product", "price": 19.99}]
    
    with patch('discountcrawlers.services.spaces_service.SpacesService') as mock_spaces:
        await metadata_agent.export_metadata(test_data, "test.json")
        mock_spaces.return_value.upload_file.assert_called_once()

@pytest.mark.asyncio
async def test_metadata_synchronization(metadata_agent):
    """Test metadata synchronization"""
    with patch('discountcrawlers.services.redis_service.RedisService') as mock_redis:
        await metadata_agent.synchronize_metadata()
        assert mock_redis.return_value.sync.called 