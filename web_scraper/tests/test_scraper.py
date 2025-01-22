from typing import List
import pytest
from scraper.utils import is_valid_url, retry_request
from unittest.mock import patch, Mock


def test_is_valid_url() -> None:
    """
    Test the is_valid_url function with valid and invalid URLs.
    """
    # Valid URLs
    assert is_valid_url("https://example.com") is True
    assert is_valid_url("http://subdomain.example.com/path?query=1") is True
    
    # Invalid URLs
    assert is_valid_url("ftp://example.com") is False
    assert is_valid_url("://missing-scheme.com") is False
    assert is_valid_url("example.com") is False
    assert is_valid_url("") is False


def test_retry_request_success() -> None:
    """
    Test retry_request function for a successful request.
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"Mock content"
    with patch("requests.get", return_value=mock_response):
        result = retry_request("https://example.com")
        assert result == b"Mock content"


def test_retry_request_failure() -> None:
    """
    Test retry_request function for a failed request.
    """
    with patch("requests.get", side_effect=Exception("Request failed")):
        with pytest.raises(Exception) as excinfo:
            retry_request("https://example.com")
        assert "Request failed" in str(excinfo.value)


def test_scraper_parse_images() -> None:
    """
    Test the WebScraper's parse_images method with a sample HTML input.
    """
    from scraper.core import WebScraper

    sample_html = """
    <html>
        <body>
            <img src="https://example.com/image1.jpg" />
            <img src="/relative/image2.jpg" />
            <img src="invalid-image-path" />
        </body>
    </html>
    """
    scraper = WebScraper(base_urls=["https://example.com"], output_dir="images")
    images = scraper.parse_images(sample_html, "https://example.com")
    assert len(images) == 2
    assert "https://example.com/image1.jpg" in images
    assert "https://example.com/relative/image2.jpg" in images


def test_scraper_download_image_success(tmp_path) -> None:
    """
    Test the WebScraper's download_image method for a successful download.
    """
    from scraper.core import WebScraper

    mock_response = Mock()
    mock_response.iter_content = lambda chunk_size: [b"content"]
    mock_response.status_code = 200

    with patch("requests.get", return_value=mock_response):
        scraper = WebScraper(base_urls=[], output_dir=str(tmp_path))
        scraper.download_image("https://example.com/image.jpg")

        # Assert the file was created
        downloaded_file = tmp_path / "image.jpg"
        assert downloaded_file.exists()
        assert downloaded_file.read_bytes() == b"content"


def test_scraper_download_image_failure() -> None:
    """
    Test the WebScraper's download_image method for a failed download.
    """
    from scraper.core import WebScraper

    with patch("requests.get", side_effect=Exception("Download failed")):
        scraper = WebScraper(base_urls=[], output_dir="images")
        with pytest.raises(Exception):
            scraper.download_image("https://example.com/image.jpg")


def test_scraper_scrape_all() -> None:
    """
    Test the WebScraper's scrape_all method for multiple URLs.
    """
    from scraper.core import WebScraper

    scraper = WebScraper(base_urls=["https://example1.com", "https://example2.com"], output_dir="images")

    with patch.object(scraper, "scrape_url") as mock_scrape_url:
        scraper.scrape_all()
        # Ensure scrape_url is called for each URL
        assert mock_scrape_url.call_count == 2
        mock_scrape_url.assert_any_call("https://example1.com")
        mock_scrape_url.assert_any_call("https://example2.com")
