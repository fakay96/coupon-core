#!/usr/bin/env python

import os
import sys
import json
import asyncio
import gzip
import requests
from xml.etree import ElementTree
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv

# crawl4ai imports
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# OpenAI + Supabase
from openai import AsyncOpenAI
from supabase import create_client, Client

load_dotenv()

# Initialize OpenAI and Supabase clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@dataclass
class ProcessedChunk:
    """
    Represents one chunk of crawled content, including discount fields
    and embeddings for search.
    """
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str

    # Potential discount fields (parsed from GPT)
    retailer: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    original_price: Optional[float] = None
    discounted_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    stock_status: Optional[str] = None

    # Extra metadata & embedding
    metadata: Dict[str, Any] = None
    embedding: List[float] = None


def chunk_text(text: str, chunk_size: int = 5000) -> List[str]:
    """
    Split text into smaller chunks, respecting code blocks and paragraphs.
    Useful for large pages or product info to facilitate GPT-based analysis.
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        snippet = text[start:end]
        # Attempt to break around code blocks (```), paragraphs, or sentence boundaries
        code_block_pos = snippet.rfind('```')
        if code_block_pos != -1 and code_block_pos > chunk_size * 0.3:
            end = start + code_block_pos
        elif '\n\n' in snippet:
            last_break = snippet.rfind('\n\n')
            if last_break > chunk_size * 0.3:
                end = start + last_break
        elif '. ' in snippet:
            last_period = snippet.rfind('. ')
            if last_period > chunk_size * 0.3:
                end = start + last_period + 1

        chunk_str = text[start:end].strip()
        if chunk_str:
            chunks.append(chunk_str)
        start = max(start + 1, end)

    return chunks


async def get_embedding(text: str) -> List[float]:
    """
    Get an embedding vector from OpenAI. Adjust to the model of your choice.
    """
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[Embedding Error] {e}")
        return [0.0] * 1536


async def parse_discount_chunk(chunk: str, url: str) -> Dict[str, Any]:
    """
    Use GPT to parse discount-related fields from the chunk.
    We return a JSON object with:
      title, summary, retailer, product_name, category,
      original_price, discounted_price, discount_percentage,
      valid_from, valid_until, stock_status

    If no discount info is found, GPT can leave them as null/empty.
    """
    system_prompt = """You are an AI that extracts discount information from chunked webpage text.
Return valid JSON with the following keys:
- title (string)
- summary (string)
- retailer (string or null)
- product_name (string or null)
- category (string or null)
- original_price (number or null)
- discounted_price (number or null)
- discount_percentage (number or null)
- valid_from (string in ISO or null)
- valid_until (string in ISO or null)
- stock_status (string, e.g. 'In Stock', 'Out of Stock', 'Unknown')

If you cannot find certain fields, set them to null or 'Unknown'. Do NOT output extra text or explanations.
"""
    try:
        # We keep response_format={"type":"json_object"} to ensure JSON parse
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"URL: {url}\n\nContent:\n{chunk[:2000]}"  # up to 2000 chars for context
                },
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        parsed_json = json.loads(response.choices[0].message.content)
        return parsed_json
    except Exception as e:
        print(f"[GPT Discount Parse Error] {e}")
        # Return fallback
        return {
            "title": "Untitled",
            "summary": "No summary",
            "retailer": None,
            "product_name": None,
            "category": None,
            "original_price": None,
            "discounted_price": None,
            "discount_percentage": None,
            "valid_from": None,
            "valid_until": None,
            "stock_status": "Unknown",
        }


async def process_chunk(chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
    """
    For a single text chunk, parse discount info via GPT + get an embedding.
    """
    # 1) GPT to parse discount fields
    discount_data = await parse_discount_chunk(chunk, url)

    # 2) Generate embedding
    embedding = await get_embedding(chunk)

    # 3) Create site-specific metadata (you can add more fields if desired)
    metadata = {
        "website": "fromaustria.com",
        "source": "dishpalai_discounts",
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path
    }

    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=discount_data.get("title", "Untitled"),
        summary=discount_data.get("summary", ""),
        content=chunk,
        retailer=discount_data.get("retailer"),
        product_name=discount_data.get("product_name"),
        category=discount_data.get("category"),
        original_price=discount_data.get("original_price"),
        discounted_price=discount_data.get("discounted_price"),
        discount_percentage=discount_data.get("discount_percentage"),
        valid_from=discount_data.get("valid_from"),
        valid_until=discount_data.get("valid_until"),
        stock_status=discount_data.get("stock_status") or "Unknown",
        metadata=metadata,
        embedding=embedding
    )


async def insert_chunk(chunk: ProcessedChunk):
    """
    Insert the ProcessedChunk into the 'discounts_data' table in Supabase.
    Matching the columns in your SQL schema.
    """
    try:
        data = {
            "url": chunk.url,
            "chunk_number": chunk.chunk_number,
            "title": chunk.title,
            "summary": chunk.summary,
            "content": chunk.content,
            "retailer": chunk.retailer,
            "product_name": chunk.product_name,
            "category": chunk.category,
            "original_price": chunk.original_price,
            "discounted_price": chunk.discounted_price,
            "discount_percentage": chunk.discount_percentage,
            "valid_from": chunk.valid_from,
            "valid_until": chunk.valid_until,
            "stock_status": chunk.stock_status,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding
        }
        result = supabase.table("discounts_data").insert(data).execute()
        print(f"[INSERT] chunk {chunk.chunk_number} for {chunk.url}")
        return result
    except Exception as e:
        print(f"[Insert Error] {e}")
        return None


async def process_and_store_document(url: str, page_markdown: str):
    """
    Chunk the crawled page text, parse discount info for each chunk,
    then store them in 'discounts_data' on Supabase.
    """
    chunks = chunk_text(page_markdown)
    tasks = [process_chunk(ch, i, url) for i, ch in enumerate(chunks)]
    processed_chunks = await asyncio.gather(*tasks)

    insert_tasks = [insert_chunk(pc) for pc in processed_chunks]
    await asyncio.gather(*insert_tasks)


async def crawl_parallel(urls: List[str], max_concurrent: int = 5):
    """
    Crawl multiple URLs in parallel using crawl4ai, with concurrency limit.
    """
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_url(u: str):
            async with semaphore:
                result = await crawler.arun(url=u, config=crawl_config, session_id="session1")
                if result.success:
                    print(f"[SUCCESS] Crawled: {u}")
                    # pass the entire markdown for chunk processing
                    await process_and_store_document(u, result.markdown_v2.raw_markdown)
                else:
                    print(f"[FAIL] {u}: {result.error_message}")

        await asyncio.gather(*(process_url(u) for u in urls))
    finally:
        await crawler.close()


def get_fromaustria_sitemap_urls() -> List[str]:
    """
    Gather and parse fromaustria.com sitemaps, returning all discovered URLs.
    """
    sitemaps = [
        "https://www.fromaustria.com/en/sitemap-c.xml",
        "https://www.fromaustria.com/en/sitemap-cs.xml",
        "https://www.fromaustria.com/en/sitemap-p.xml",
        "https://www.fromaustria.com/en/sitemap-p404.xml",
        "https://www.fromaustria.com/en/sitemap-i.xml",
        "https://www.fromaustria.com/en/sitemap-sp.xml",
        "https://www.fromaustria.com/en/sitemap-r.xml",
        "https://www.fromaustria.com/en/update.rss"
    ]

    all_urls = []
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    for sitemap_url in sitemaps:
        try:
            print(f"[Fetch Sitemap] {sitemap_url}")
            response = requests.get(sitemap_url, timeout=15)
            response.raise_for_status()
            content = response.content

            # If .rss or .xml, attempt to parse. If .gz, you'd decompress first.
            root = ElementTree.fromstring(content)
            for loc in root.findall(".//ns:loc", ns):
                if loc.text:
                    all_urls.append(loc.text.strip())
        except Exception as e:
            print(f"[Sitemap Error] Could not parse {sitemap_url}: {e}")

    unique_urls = sorted(set(all_urls))
    print(f"[INFO] Extracted {len(unique_urls)} total URLs from fromaustria.com sitemaps.")
    return unique_urls


async def main():
    # 1) Retrieve all fromaustria.com sitemap URLs
    urls = get_fromaustria_sitemap_urls()
    if not urls:
        print("[No URLs] No sitemap URLs found to crawl.")
        return

    print(f"[INFO] Found {len(urls)} URLs to crawl from fromaustria sitemaps.")
    # 2) Crawl them in parallel
    await crawl_parallel(urls, max_concurrent=5)


if __name__ == "__main__":
    asyncio.run(main())
