import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pyrate_limiter import Duration, Limiter, Rate, BucketFullException

from .utils import (
    is_valid_url,
    retry_request,
    extract_discount_code,
    extract_discount_description,
    extract_expiration_date,
    extract_location,
    extract_retailer_name,
)
from .kafka_producer import send_discount_data  # Import the producer
import time
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
rate = Rate(10, Duration.MINUTE)
limiter = Limiter(rate)


class WebScraper:
    """
    A class to scrape images and discount data from a list of URLs.
    """

    def __init__(self, base_urls: List[str], output_dir: str, max_workers: int = 5) -> None:
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

    def fetch_html(self, url: str) -> str:
        """
        Fetch the HTML content of a given URL with rate limiting.

        Args:
            url (str): The URL to fetch HTML from.

        Returns:
            str: The HTML content of the URL.
        """
        logging.info(f"Fetching HTML from {url}")

        # Apply rate limiting
        try:
            limiter.try_acquire("scrape")  # Enforce rate limit for "scrape" identity
        except BucketFullException as e:
            wait_time = e.meta_info["remaining_time"]
            logging.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds...")
            raise

        try:
            response_content = retry_request(url)
            if not response_content:
                logging.warning(f"No HTML content returned from {url}")
            return response_content
        except Exception as e:
            logging.error(f"Error fetching HTML from {url}: {e}")
            raise

    def parse_images(self, html: str, base_url: str) -> List[str]:
        """
        Parse image URLs from the HTML content.

        Args:
            html (str): HTML content of the page.
            base_url (str): Base URL for resolving relative image paths.

        Returns:
            List[str]: A list of valid, absolute image URLs.
        """
        if not html:
            logging.warning("Empty HTML content; cannot parse images.")
            return []
        soup = BeautifulSoup(html, "html.parser")
        img_tags = soup.find_all("img")
        img_urls = [urljoin(base_url, img.get("src", "")) for img in img_tags]
        valid_urls = [url for url in img_urls if is_valid_url(url)]
        logging.info(f"Found {len(valid_urls)} valid image URLs at {base_url}")
        return valid_urls

    def download_image(self, image_url: str) -> None:
        """
        Download a single image.

        Args:
            image_url (str): The URL of the image to download.
        """
        try:
            response_content = retry_request(image_url)
            if response_content:
                file_name = os.path.join(self.output_dir, os.path.basename(image_url))
                with open(file_name, "wb") as file:
                    file.write(response_content)
                logging.info(f"Downloaded image: {file_name}")
            else:
                logging.error(f"No response received when downloading {image_url}")
        except Exception as e:
            logging.error(f"Failed to download {image_url}: {e}")

    def process_discount_data(self, html: str) -> dict:
        """
        Extract discount data from HTML.

        Args:
            html (str): The HTML content to extract data from.

        Returns:
            dict: A dictionary containing discount data.
        """
        discount_data = {}
        try:
            discount_data = {
                "retailer_name": extract_retailer_name(html),
                "description": extract_discount_description(html),
                "discount_code": extract_discount_code(html),
                "expiration_date": extract_expiration_date(html),
                "location": extract_location(html),
            }
            logging.info(f"Extracted discount data: {discount_data}")
        except Exception as e:
            logging.error(f"Error extracting discount data: {e}")
        return discount_data

    def scrape_url(self, url: str) -> None:
        """
        Scrape images and discount data from a single URL.

        Args:
            url (str): The URL to scrape.
        """
        logging.info(f"Scraping URL: {url}")
        
        # Fetch HTML with rate limiting
        try:
            html = self.fetch_html(url)
        except BucketFullException as e:
            wait_time = e.meta_info["remaining_time"]
            logging.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds...")
            return
        except Exception as e:
            logging.error(f"Skipping URL {url} due to fetch error: {e}")
            return

        # Download images concurrently
        images = self.parse_images(html, url)
        
        if images:
            try:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {executor.submit(self.download_image, img_url): img_url for img_url in images}
                    for future in as_completed(futures):
                        img_url = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            logging.error(f"Error in downloading image {img_url}: {e}")
            except Exception as e:
                logging.error(f"Error during concurrent image download for {url}: {e}")
        
        # Extract and send discount data to Kafka
        discount_data = self.process_discount_data(html)
        
        if discount_data:
            try:
                send_discount_data(discount_data)
                logging.info("Discount data sent to Kafka successfully.")
            except Exception as e:
                logging.error(f"Failed to send discount data to Kafka: {e}")

    def scrape_all(self) -> None:
        """
        Scrape images and discount data from all base URLs.
        If the list of URLs is empty, wait and retry.
        """
        logging.info("Starting the scraping process for all URLs.")

        while True:  # Infinite loop to keep retrying if URLs are empty
            if not self.base_urls:
                logging.warning("No URLs to scrape. Sleeping for 60 seconds before retrying...")
                time.sleep(60)  # Sleep for 60 seconds before checking again
                continue

            for url in self.base_urls:
                if not is_valid_url(url):  # Validate URL before scraping
                    logging.warning(f"Invalid URL skipped: {url}")
                    continue

                try:
                    self.scrape_url(url)
                except Exception as e:
                    logging.error(f"Unexpected error while scraping {url}: {e}")

            logging.info("Scraping process completed.")
            break  # Exit the loop once scraping is done
