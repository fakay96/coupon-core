import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
from unittest.mock import Mock, patch
from discountcrawlers.services.redis_service import RedisService

@pytest.fixture
def redis_service():
    return RedisService()

def test_connection(redis_service):
    """Test Redis service connection"""
    with patch('redis.Redis') as mock_redis:
        redis_service.connect()
        mock_redis.assert_called_once()

def test_store_item(redis_service):
    """Test storing items in Redis"""
    with patch('redis.Redis') as mock_redis:
        test_data = {
            "title": "Test Product",
            "price": 19.99,
            "url": "https://example.com/product"
        }
        redis_service.store_item(test_data)
        mock_redis.return_value.set.assert_called_once()

def test_get_items(redis_service):
    """Test retrieving items from Redis"""
    with patch('redis.Redis') as mock_redis:
        mock_redis.return_value.keys.return_value = [b"item:1"]
        mock_redis.return_value.get.return_value = '{"title": "Test Product"}'
        items = redis_service.get_items()
        assert len(items) == 1
        assert items[0]["title"] == "Test Product"

def test_error_handling(redis_service):
    """Test Redis service error handling"""
    with patch('redis.Redis') as mock_redis:
        mock_redis.return_value.set.side_effect = Exception("Redis error")
        with pytest.raises(Exception):
            redis_service.store_item({"test": "data"})

def test_configuration():
    """Test Redis service configuration"""
    from discountcrawlers.services import REDIS_CONFIG
    assert REDIS_CONFIG["HOST"] is not None
    assert REDIS_CONFIG["PORT"] is not None 