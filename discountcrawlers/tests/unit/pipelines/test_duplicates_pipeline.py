import pytest
from datetime import datetime
from discountcrawlers.items import DiscountItem
from discountcrawlers.pipelines import DuplicatesPipeline

@pytest.fixture
def duplicates_pipeline():
    return DuplicatesPipeline()

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

def test_first_occurrence(duplicates_pipeline, sample_item):
    """Test handling of first occurrence of an item"""
    processed_item = duplicates_pipeline.process_item(sample_item, None)
    assert processed_item == sample_item

def test_duplicate_item(duplicates_pipeline, sample_item):
    """Test handling of duplicate items"""
    # First occurrence
    duplicates_pipeline.process_item(sample_item, None)
    
    # Duplicate item
    duplicate_item = DiscountItem(
        title="Test Product",
        price=19.99,
        original_price=29.99,
        url="https://example.com/product",  # Same URL
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now()
    )
    processed_duplicate = duplicates_pipeline.process_item(duplicate_item, None)
    assert processed_duplicate is None  # Should be filtered out

def test_different_items(duplicates_pipeline, sample_item):
    """Test handling of different items"""
    # First item
    duplicates_pipeline.process_item(sample_item, None)
    
    # Different item
    different_item = DiscountItem(
        title="Different Product",
        price=29.99,
        original_price=39.99,
        url="https://example.com/different",
        store="Test Store",
        valid_from=datetime.now(),
        valid_to=datetime.now()
    )
    processed_different = duplicates_pipeline.process_item(different_item, None)
    assert processed_different == different_item  # Should be processed 