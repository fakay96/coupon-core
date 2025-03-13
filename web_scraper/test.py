import asyncio
import aiohttp
import pandas as pd
import json
import random
import time
import cloudscraper
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib
class DiscountCrawler:
    def __init__(self, urls, max_depth=2, use_selenium=True, use_cloudscraper=True):
        """
        Initialize the crawler with multiple URLs.
        """
        self.urls = urls
        self.max_depth = max_depth
        self.visited = set()
        self.collected_products = []
        self.failed_urls = []
        self.use_selenium = use_selenium
        self.use_cloudscraper = use_cloudscraper
        self.scraper = cloudscraper.create_scraper()
        
        # Randomized User-Agent headers
        self.USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0 Safari/537.36"
        ]
        
        # Rotating proxies (Use your own paid proxy list)
        self.proxies = [
            "http://user:pass@proxy1.com:8080",
            "http://user:pass@proxy2.com:8080",
            "http://user:pass@proxy3.com:8080"
        ]

        # Set up Selenium WebDriver
        if self.use_selenium:
            options = uc.ChromeOptions()
            options.headless = True
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={random.choice(self.USER_AGENTS)}")
            self.driver = uc.Chrome(options=options)

    async def fetch(self, session, url, retries=3):
        """
        Asynchronously fetch a URL with retries for 403 errors.
        """
        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Referer": "https://www.google.com/"
        }
        proxy = random.choice(self.proxies) if self.proxies else None

        for attempt in range(retries):
            try:
                async with session.get(url, headers=headers, proxy=proxy, timeout=20, ssl=False) as response:
                    if response.status == 403:
                        print(f"❌ 403 Forbidden: {url} - Retrying with Cloudscraper/Selenium...")
                        return self.fetch_with_cloudscraper_or_selenium(url)
                    if response.status != 200:
                        print(f"❌ Failed to retrieve {url}: Status {response.status}")
                        return None
                    return await response.text()
            except Exception as e:
                print(f"⚠️ Error fetching {url}: {e}")
                await asyncio.sleep(2**attempt)  # Exponential backoff

        print(f"❌ Max retries reached for {url}, switching to Cloudscraper/Selenium...")
        return self.fetch_with_cloudscraper_or_selenium(url)

    def fetch_with_cloudscraper_or_selenium(self, url):
        """
        Use Cloudscraper (for Cloudflare bypass) or Selenium for JavaScript-heavy pages.
        """
        if self.use_cloudscraper:
            print(f"🔄 Trying Cloudscraper for: {url}")
            try:
                response = self.scraper.get(url)
                if response.status_code == 200:
                    return response.text
            except Exception as e:
                print(f"⚠️ Cloudscraper failed: {e}")

        if self.use_selenium:
            print(f"🌐 Trying Selenium for: {url}")
            try:
                self.driver.get(url)
                time.sleep(random.uniform(3, 6))  # Prevent bot detection
                return self.driver.page_source
            except Exception as e:
                print(f"❌ Selenium failed for {url}: {e}")
                return None

    async def process_page(self, session, url, depth, store_name):
        """
        Process a single page:
        - Fetch content
        - Extract structured product data
        - Extract discount prices
        - Extract categories
        - Follow pagination links
        """
        if url in self.visited or depth < 0:
            return
        self.visited.add(url)
        print(f"\n🔍 Crawling: {url}")

        html = await self.fetch(session, url)
        if not html:
            self.failed_urls.append(url)
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Extract product details
        product_cards = soup.find_all("div", class_="product-card")
        for card in product_cards:
            product_info = {
                "name": card.find("h3").get_text(strip=True) if card.find("h3") else "Unknown",
                "category": card.get("data-category", "General"),
                "url": urllib.parse.urljoin(url, card.find("a")["href"]) if card.find("a") else "N/A",
            }
            self.collected_products.append(product_info)

    async def run(self):
        """ Start the asynchronous crawling process for all URLs. """
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_page(session, url["url"], self.max_depth, url["store"]) for url in self.urls]
            await asyncio.gather(*tasks)

        self.save_output()

    def save_output(self):
        """ Save collected discount data to CSV and JSON files. """
        pd.DataFrame(self.collected_products).to_csv("discounts.csv", index=False)
        with open("discounts.json", "w", encoding="utf-8") as json_file:
            json.dump(self.collected_products, json_file, ensure_ascii=False, indent=4)

        if self.failed_urls:
            with open("failed_urls.txt", "w") as f:
                f.write("\n".join(self.failed_urls))

        print("✅ Output saved to discounts.csv and discounts.json")

# Load URLs from CSV
df = pd.read_csv("urls.csv").dropna(subset=["Links"])
urls = [{"url": row["Links"], "store": row["Store"]} for _, row in df.iterrows()]

# Run the scraper
if __name__ == "__main__":
    crawler = DiscountCrawler(urls=urls, max_depth=2, use_selenium=True, use_cloudscraper=True)
    asyncio.run(crawler.run())
