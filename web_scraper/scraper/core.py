import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pyrate_limiter import Duration, Limiter, MemoryStorage, RequestRate

from .utils import is_valid_url, retry_request

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/scraper.log"),
        logging.StreamHandler(),
    ],
)

# Rate limiter to control the number of requests (10 requests per minute)
rate = RequestRate(10, Duration.MINUTE)
storage = MemoryStorage()
limiter = Limiter(rate, storage=storage)


class WebScraper:
    """
    A class to scrape images from a list of URLs.

    Attributes:
        base_urls (List[str]): A list of base URLs to scrape.
        output_dir (str): Directory to save downloaded images.
        max_workers (int): Max threads for concurrent downloads.
    """

    def __init__(
        self, base_urls: List[str], output_dir: str, max_workers: int = 5
    ) -> None:
        """
        Initialize the WebScraper instance.

        Args:
            base_urls (List[str]): A list of URLs to scrape.
            output_dir (str): Directory to save downloaded images.
            max_workers (int): Number of threads for concurrent downloads.
        """
        self.base_urls = base_urls
        self.output_dir = output_dir
        self.max_workers = max_workers
        os.makedirs(output_dir, exist_ok=True)

    @limiter.ratelimit("scrape", delay=True)
    def fetch_html(self, url: str) -> str:
        """
        Fetch the HTML content of a given URL.

        Args:
            url (str): The URL to fetch HTML from.

        Returns:
            str: The HTML content of the URL.
        """
        logging.info(f"Fetching HTML from {url}")
        return retry_request(url)

    def parse_images(self, html: str, base_url: str) -> List[str]:
        """
        Parse image URLs from the HTML content.

        Args:
            html (str): HTML content of the page.
            base_url (str): Base URL for resolving relative image paths.

        Returns:
            List[str]: A list of valid, absolute image URLs.
        """
        soup = BeautifulSoup(html, "html.parser")
        img_tags = soup.find_all("img")
        img_urls = [urljoin(base_url, img.get("src", "")) for img in img_tags]
        return [url for url in img_urls if is_valid_url(url)]

    def download_image(self, image_url: str) -> None:
        """
        Download a single image.

        Args:
            image_url (str): The URL of the image to download.

        Raises:
            Exception: Logs an error if the download fails.
        """
        try:
            response = retry_request(image_url)
            file_name = os.path.join(self.output_dir, os.path.basename(image_url))
            with open(file_name, "wb") as file:
                file.write(response)
            logging.info(f"Downloaded: {file_name}")
        except Exception as e:
            logging.error(f"Failed to download {image_url}: {e}")

    def scrape_url(self, url: str) -> None:
        """
        Scrape images from a single URL.

        Args:
            url (str): The URL to scrape.
        """
        try:
            html = self.fetch_html(url)
            images = self.parse_images(html, url)
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                executor.map(self.download_image, images)
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")

    def scrape_all(self) -> None:
        """
        Scrape images from all base URLs.

        This method iterates through the list of URLs and invokes
        the `scrape_url` method for each.
        """
        for url in self.base_urls:
            logging.info(f"Starting scrape for {url}")
            self.scrape_url(url)
        logging.info("Scraping completed.")
