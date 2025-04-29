import pytest
from unittest.mock import Mock, patch, AsyncMock
from discountcrawlers.utils.redis_utils import RedisUtils
from discountcrawlers.items import DiscountItem
from datetime import datetime, timedelta

@pytest.fixture
def redis_utils():
    return RedisUtils()

@pytest.fixture
def sample_item():
    return DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now() + timedelta(days=7)
    )

@pytest.mark.asyncio
async def test_redis_connection(redis_utils):
    """Test Redis connection"""
    with patch('redis.asyncio.Redis') as mock_redis:
        await redis_utils.connect()
        mock_redis.assert_called_once()
        assert redis_utils.redis is not None

@pytest.mark.asyncio
async def test_item_storage(redis_utils, sample_item):
    """Test storing items in Redis"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.set = AsyncMock()
        await redis_utils.store_item(sample_item)
        mock_redis.return_value.set.assert_called_once()

@pytest.mark.asyncio
async def test_item_retrieval(redis_utils, sample_item):
    """Test retrieving items from Redis"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.get = AsyncMock(return_value=sample_item.to_json())
        item = await redis_utils.get_item(sample_item.url)
        assert item is not None
        assert item.title == sample_item.title
        assert item.price == sample_item.price

@pytest.mark.asyncio
async def test_batch_operations(redis_utils, sample_item):
    """Test batch operations"""
    items = [sample_item] * 3
    
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.pipeline = Mock(return_value=mock_redis)
        mock_redis.set = AsyncMock()
        mock_redis.execute = AsyncMock()
        
        await redis_utils.store_items(items)
        assert mock_redis.set.call_count == len(items)
        mock_redis.execute.assert_called_once()

@pytest.mark.asyncio
async def test_item_expiration(redis_utils, sample_item):
    """Test item expiration handling"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.ttl = AsyncMock(return_value=3600)
        ttl = await redis_utils.get_item_ttl(sample_item.url)
        assert ttl == 3600

@pytest.mark.asyncio
async def test_error_handling(redis_utils):
    """Test error handling"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.get = AsyncMock(side_effect=Exception("Redis error"))
        with pytest.raises(Exception):
            await redis_utils.get_item("invalid_url")

@pytest.mark.asyncio
async def test_connection_pooling(redis_utils):
    """Test connection pooling"""
    with patch('redis.asyncio.ConnectionPool') as mock_pool:
        await redis_utils.connect()
        mock_pool.assert_called_once()
        assert redis_utils.pool is not None

@pytest.mark.asyncio
async def test_cleanup(redis_utils):
    """Test cleanup operations"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.flushdb = AsyncMock()
        await redis_utils.cleanup()
        mock_redis.return_value.flushdb.assert_called_once()

@pytest.mark.asyncio
async def test_health_check(redis_utils):
    """Test health check"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.ping = AsyncMock(return_value=True)
        is_healthy = await redis_utils.check_health()
        assert is_healthy is True

@pytest.mark.asyncio
async def test_metrics_collection(redis_utils):
    """Test metrics collection"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.info = AsyncMock(return_value={
            'used_memory': 1024,
            'connected_clients': 1
        })
        metrics = await redis_utils.get_metrics()
        assert 'used_memory' in metrics
        assert 'connected_clients' in metrics 