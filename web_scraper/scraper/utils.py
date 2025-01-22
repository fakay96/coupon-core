import requests
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def retry_request(url: str, timeout: int = 10) -> bytes:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content

def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)
