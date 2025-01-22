import os
from dotenv import load_dotenv

load_dotenv()

BASE_URLS = os.getenv("BASE_URLS", "").split(",")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "images")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 5))
