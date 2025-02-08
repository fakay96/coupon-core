from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
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
def extract_retailer_name(html: str) -> str:
    """
    Extract the retailer name from the HTML content.

    Args:
        html (str): The HTML content of the page.

    Returns:
        str: The name of the retailer.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Logic to extract retailer name (placeholder logic)
    retailer_name = soup.find("h1", class_="retailer-name").text.strip()
    return retailer_name

def extract_discount_description(html: str) -> str:
    """
    Extract the discount description from the HTML content.

    Args:
        html (str): The HTML content of the page.

    Returns:
        str: The description of the discount.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Logic to extract discount description (placeholder logic)
    description = soup.find("div", class_="discount-description").text.strip()
    return description

def extract_discount_code(html: str) -> str:
    """
    Extract the discount code from the HTML content.

    Args:
        html (str): The HTML content of the page.

    Returns:
        str: The discount code.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Logic to extract discount code (placeholder logic)
    discount_code = soup.find("span", class_="discount-code").text.strip()
    return discount_code

def extract_expiration_date(html: str) -> str:
    """
    Extract the expiration date from the HTML content.

    Args:
        html (str): The HTML content of the page.

    Returns:
        str: The expiration date of the discount.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Logic to extract expiration date (placeholder logic)
    expiration_date = soup.find("span", class_="expiration-date").text.strip()
    return expiration_date

def extract_location(html: str) -> str:
    """
    Extract the location from the HTML content.

    Args:
        html (str): The HTML content of the page.

    Returns:
        str: The location where the discount is valid.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Logic to extract location (placeholder logic)
    location = soup.find("span", class_="location").text.strip()
    return location
