from scraper.core import WebScraper
from scraper.config import BASE_URLS, OUTPUT_DIR, MAX_WORKERS

if __name__ == "__main__":
    scraper = WebScraper(base_urls=BASE_URLS, output_dir=OUTPUT_DIR, max_workers=MAX_WORKERS)
    scraper.scrape_all()
