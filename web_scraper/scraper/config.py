import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Base URLs to scrape, retrieved from environment variables
BASE_URLS = os.getenv("BASE_URLS", "").split(",")

# Directory where downloaded images will be stored
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "images")

# Maximum number of threads for concurrent downloads
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))
