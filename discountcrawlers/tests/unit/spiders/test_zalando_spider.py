import pytest
from unittest.mock import Mock, patch
from scrapy.http import HtmlResponse, Request
from discountcrawlers.spiders.zalando_spider import ZalandoSpider
from discountcrawlers.items import DiscountItem

@pytest.fixture
def zalando_spider():
    return ZalandoSpider()

@pytest.fixture
def sample_html():
    return """
    <html>
        <div class="product">
            <h2>Test Product</h2>
            <span class="price">19.99</span>
            <a href="https://example.com/product">Link</a>
        </div>
    </html>
    """

def test_start_requests(zalando_spider):
    """Test Zalando spider start requests"""
    requests = list(zalando_spider.start_requests())
    assert len(requests) == 1
    assert isinstance(requests[0], Request)
    assert "zalando.de" in requests[0].url

def test_parse(zalando_spider, sample_html):
    """Test Zalando spider parsing"""
    response = HtmlResponse(
        url="https://www.zalando.de/angebote",
        body=sample_html.encode(),
        encoding='utf-8'
    )
    
    items = list(zalando_spider.parse(response))
    assert len(items) == 1
    assert isinstance(items[0], DiscountItem)
    assert items[0]["title"] == "Test Product"
    assert items[0]["price"] == 19.99
    assert items[0]["url"] == "https://example.com/product"

def test_pagination(zalando_spider):
    """Test Zalando spider pagination"""
    html = """
    <html>
        <div class="pagination">
            <a href="?page=2">Next</a>
        </div>
    </html>
    """
    response = HtmlResponse(
        url="https://www.zalando.de/angebote",
        body=html.encode(),
        encoding='utf-8'
    )
    requests = list(zalando_spider.parse(response))
    assert len(requests) == 1
    assert "page=2" in requests[0].url

def test_error_handling(zalando_spider):
    """Test Zalando spider error handling"""
    invalid_html = "<html><body>Invalid content</body></html>"
    response = HtmlResponse(
        url="https://example.com",
        body=invalid_html.encode(),
        encoding='utf-8'
    )
    items = list(zalando_spider.parse(response))
    assert len(items) == 0

def test_settings(zalando_spider):
    """Test Zalando spider settings"""
    assert zalando_spider.custom_settings["ROBOTSTXT_OBEY"] is True
    assert "PLAYWRIGHT_LAUNCH_OPTIONS" in zalando_spider.custom_settings 