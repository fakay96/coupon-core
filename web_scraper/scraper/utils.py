from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def retry_request(url: str, timeout: int = 10) -> bytes:
    """
    Perform an HTTP GET request with retries.

    Retries up to 3 times using exponential backoff in case of failures.

    Args:
        url (str): The URL to fetch.
        timeout (int): Timeout for the request in seconds.

    Returns:
        bytes: The content of the HTTP response.

    Raises:
        requests.RequestException: If the request fails after retries.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def is_valid_url(url: str) -> bool:
    """
    Validate the structure of a URL.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is valid, otherwise False.
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)
