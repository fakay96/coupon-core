import os
from typing import List
import logging
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from .utils import retry_request, is_valid_url
from bs4 import BeautifulSoup
from pyrate_limiter import Limiter, Duration, RequestRate, MemoryStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/scraper.log"), logging.StreamHandler()],
)

rate = RequestRate(10, Duration.MINUTE)
storage = MemoryStorage()
limiter = Limiter(rate, storage=storage)

class WebScraper:
    def __init__(self, base_urls: List[str], output_dir: str, max_workers: int = 5) -> None:
        self.base_urls = base_urls
        self.output_dir = output_dir
        self.max_workers = max_workers
        os.makedirs(output_dir, exist_ok=True)

    @limiter.ratelimit("scrape", delay=True)
    def fetch_html(self, url: str) -> str:
        logging.info(f"Fetching HTML from {url}")
        return retry_request(url)

    def parse_images(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        img_tags = soup.find_all("img")
        img_urls = [urljoin(base_url, img.get("src", "")) for img in img_tags]
        return [url for url in img_urls if is_valid_url(url)]

    def download_image(self, image_url: str) -> None:
        try:
            response = retry_request(image_url)
            file_name = os.path.join(self.output_dir, os.path.basename(image_url))
            with open(file_name, "wb") as file:
                file.write(response)
            logging.info(f"Downloaded: {file_name}")
        except Exception as e:
            logging.error(f"Failed to download {image_url}: {e}")

    def scrape_url(self, url: str) -> None:
        try:
            html = self.fetch_html(url)
            images = self.parse_images(html, url)
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                executor.map(self.download_image, images)
        except Exception as e:
            logging.error(f"Error scraping {url}: {e}")

    def scrape_all(self) -> None:
        for url in self.base_urls:
            logging.info(f"Starting scrape for {url}")
            self.scrape_url(url)
        logging.info("Scraping completed.")
