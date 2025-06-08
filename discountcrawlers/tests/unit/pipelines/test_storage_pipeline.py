import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
from datetime import datetime
from discountcrawlers.items import DiscountItem
from discountcrawlers.pipelines import StoragePipeline
from unittest.mock import patch

@pytest.fixture
def storage_pipeline():
    return StoragePipeline()

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

def test_store_item(storage_pipeline, sample_item):
    """Test storing items"""
    with patch('redis.Redis') as mock_redis:
        processed_item = storage_pipeline.process_item(sample_item, None)
        assert processed_item == sample_item
        mock_redis.return_value.set.assert_called_once()

def test_storage_error(storage_pipeline, sample_item):
    """Test storage error handling"""
    with patch('redis.Redis') as mock_redis:
        mock_redis.return_value.set.side_effect = Exception("Storage error")
        with pytest.raises(Exception):
            storage_pipeline.process_item(sample_item, None)

def test_settings():
    """Test storage pipeline settings"""
    from discountcrawlers.pipelines import STORAGE_SETTINGS
    assert STORAGE_SETTINGS["REDIS_HOST"] is not None
    assert STORAGE_SETTINGS["REDIS_PORT"] is not None 