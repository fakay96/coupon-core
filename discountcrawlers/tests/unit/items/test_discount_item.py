import pytest
from datetime import datetime
from discountcrawlers.items import DiscountItem

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

def test_item_creation(sample_item):
    """Test DiscountItem creation"""
    assert sample_item["title"] == "Test Product"
    assert sample_item["price"] == 19.99
    assert sample_item["original_price"] == 29.99
    assert sample_item["url"] == "https://example.com/product"
    assert sample_item["store"] == "Test Store"
    assert isinstance(sample_item["valid_from"], datetime)
    assert isinstance(sample_item["valid_to"], datetime)

def test_item_validation():
    """Test DiscountItem validation"""
    # Test with missing required fields
    with pytest.raises(KeyError):
        DiscountItem(
            title="Test Product",
            price=19.99
        )
    
    # Test with invalid price
    with pytest.raises(ValueError):
        DiscountItem(
            title="Test Product",
            price=-10.0,
            url="https://example.com/product",
            store="Test Store"
        )

def test_item_serialization(sample_item):
    """Test DiscountItem serialization"""
    item_dict = dict(sample_item)
    assert isinstance(item_dict, dict)
    assert item_dict["title"] == "Test Product"
    assert item_dict["price"] == 19.99
    assert item_dict["url"] == "https://example.com/product"

def test_item_deserialization():
    """Test DiscountItem deserialization"""
    item_dict = {
        "title": "Test Product",
        "price": 19.99,
        "original_price": 29.99,
        "url": "https://example.com/product",
        "store": "Test Store",
        "valid_from": datetime.now().isoformat(),
        "valid_to": datetime.now().isoformat()
    }
    item = DiscountItem(item_dict)
    assert item["title"] == "Test Product"
    assert item["price"] == 19.99
    assert item["url"] == "https://example.com/product" 