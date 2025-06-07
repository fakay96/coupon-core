import pytest
from geodiscounts.v1.views.discount_process_view import ImportDiscountsAPIView


@pytest.mark.parametrize("url,expected", [
    ("https://bucket.nyc3.digitaloceanspaces.com/path/data.json", None),
    ("ftp://bucket.nyc3.digitaloceanspaces.com/data.json", "http or https"),
    ("https://example.com/data.json", "digitaloceanspaces"),
    ("https://bucket.nyc3.digitaloceanspaces.com/data.txt", "JSON"),
    ("https://bucket.nyc3.digitaloceanspaces.com/.json", "valid file path"),
])
def test_validate_file_url(url, expected):
    view = ImportDiscountsAPIView()
    error = view._validate_file_url(url)
    if expected is None:
        assert error is None
    else:
        assert expected.lower() in error.lower()
