"""
Google Generative AI embedding helper with direct HTTP requests
=============================================================

• Embeds text via **models/text‑embedding‑004** (768‑D) using direct API calls
• Optional coarse categorisation with *gemini‑1.5‑flash* or *gemini-2.0-flash*
• Sync helpers (`generate_embedding`, `generate_embeddings_batch`)
• Async wrapper (`EmbeddingUtils`) with proper concurrency controls
• Twisted‑friendly `generate_embedding_deferred`
• Thread-safe implementation with proper locks and local state
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import concurrent.futures
import requests
import aiohttp
import numpy as np
from dotenv import load_dotenv
from twisted.internet import defer, threads

load_dotenv()
LOGGER = logging.getLogger(__name__)

# ───────────────────────── configuration ──────────────────────────
EMBED_MODEL = "models/text-embedding-004"
CATEGORISER_MODEL = "gemini-2.0-flash"
EMB_DIM = 768
MAX_BATCH = 100  # Reduced batch size to avoid rate limits
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 10  # seconds

# Thread-safety locks
_api_init_lock = threading.RLock()
_categorise_lock = threading.RLock()

CATEGORIES: Dict[str, str] = {
    "flight": "Travel and flight‑related deals",
    "fashion": "Clothing and accessories",
    "furniture": "Home furniture and decor",
    "electronics": "Electronic devices and gadgets",
    "grocery": "Food and grocery items",
}

# Thread-local storage for session objects
_thread_local = threading.local()

# ───────────────────── API bootstrap ───────────────────────────────

def _get_api_key() -> Optional[str]:
    """Get the API key from environment variable"""
    with _api_init_lock:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            LOGGER.error("GEMINI_API_KEY env var not set")
            return None
        return key

def _get_session() -> requests.Session:
    """Get or create a thread-local requests session"""
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session

def _exponential_backoff(attempt: int) -> float:
    """Calculate exponential backoff delay with jitter"""
    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
    jitter = delay * 0.1 * np.random.random()  # Add 10% jitter
    return delay + jitter

# ───────────────────── response helpers ───────────────────────────

def _vec(obj: Any) -> Optional[np.ndarray]:
    """Extract vector values from API responses"""
    try:
        # Handle dictionaries first
        if isinstance(obj, dict):
            if "values" in obj:
                return np.asarray(obj["values"], np.float32)
            if "embedding" in obj:
                return np.asarray(obj["embedding"], np.float32)
        # Handle objects with .values attribute (non-dict)
        if hasattr(obj, "values") and not isinstance(obj, dict):
            values = obj.values
            if callable(values):
                values = values()
            return np.asarray(values, np.float32)
        # Handle raw lists
        if isinstance(obj, list):
            return np.asarray(obj, np.float32)
    except Exception as exc:
        LOGGER.error("Vector conversion failed: %s", exc)
    return None

def _extract_embedding_from_response(response_data: Dict) -> Optional[np.ndarray]:
    """Extract embedding from API response"""
    try:
        LOGGER.debug(f"Extracting embedding from response: {json.dumps(response_data, indent=2)}")
        
        # Single embedding response format
        if "embedding" in response_data and "values" in response_data["embedding"]:
            vec = _vec(response_data["embedding"]["values"])
            LOGGER.debug(f"Found 'embedding.values' key, extracted vector shape: {vec.shape if vec is not None else None}")
            return vec
            
        if "embedding" in response_data:
            vec = _vec(response_data["embedding"])
            LOGGER.debug(f"Found 'embedding' key, extracted vector: {vec.shape if vec is not None else None}")
            return vec
            
        if "embeddings" in response_data and response_data["embeddings"]:
            vec = _vec(response_data["embeddings"][0])
            LOGGER.debug(f"Found 'embeddings' key, extracted vector: {vec.shape if vec is not None else None}")
            return vec
            
        if "data" in response_data and response_data["data"]:
            vec = _vec(response_data["data"][0])
            LOGGER.debug(f"Found 'data' key, extracted vector: {vec.shape if vec is not None else None}")
            return vec
            
        LOGGER.error(f"No valid embedding data found in response. Available keys: {list(response_data.keys())}")
        return None
        
    except Exception as exc:
        LOGGER.error(f"Failed to extract embedding: {exc}")
        return None

def _extract_batch_from_response(response_data: Dict, want: int):
    """Handle batch response structure"""
    try:
        LOGGER.debug(f"Extracting batch embeddings from response: {json.dumps(response_data, indent=2)}")
        
        # Single embedding response format
        if "embedding" in response_data and "values" in response_data["embedding"]:
            vec = _vec(response_data["embedding"]["values"])
            LOGGER.debug(f"Found single 'embedding.values' key, extracted vector shape: {vec.shape if vec is not None else None}")
            return [vec] * want  # Return the same embedding for all items in batch
            
        # Modern batch response format
        if "embeddings" in response_data:
            vecs = [_vec(e) for e in response_data["embeddings"]]
            LOGGER.debug(f"Found 'embeddings' key, extracted {len(vecs)} vectors")
            return vecs
            
        # Legacy batch format
        if "data" in response_data:
            vecs = [_vec(item["embedding"]) for item in response_data["data"]]
            LOGGER.debug(f"Found 'data' key, extracted {len(vecs)} vectors")
            return vecs
            
        LOGGER.error(f"No valid batch embedding data found in response. Available keys: {list(response_data.keys())}")
        return [None] * want
        
    except KeyError as exc:
        LOGGER.error(f"Missing embedding key: {exc}")
        return [None] * want
    except Exception as exc:
        LOGGER.error(f"Failed to extract batch embeddings: {exc}")
        return [None] * want

# ───────────────────── direct API calls ───────────────────────────

def _embed_single_direct(text: str) -> Optional[np.ndarray]:
    """Embed a single text using direct API call with retries"""
    api_key = _get_api_key()
    if not api_key:
        return None
    url = f"{BASE_URL}/{EMBED_MODEL}:embedContent?key={api_key}"
    payload = {
        "content": {"parts": [{"text": text}]}
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            session = _get_session()
            response = session.post(url, json=payload)
            
            if response.status_code == 429:
                delay = _exponential_backoff(attempt)
                LOGGER.warning(f"Rate limited. Retry {attempt + 1}/{MAX_RETRIES}. Waiting {delay:.1f}s...")
                time.sleep(delay)
                continue
                
            response.raise_for_status()
            data = response.json()
            return _extract_embedding_from_response(data)
            
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                LOGGER.error("Single embed API call failed after %d retries: %s", MAX_RETRIES, exc)
                return None
            delay = _exponential_backoff(attempt)
            LOGGER.warning(f"API call failed. Retry {attempt + 1}/{MAX_RETRIES}. Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    return None

def _embed_batch_direct(texts: List[str]) -> List[Optional[np.ndarray]]:
    """Embed a batch of texts using direct API call with retries"""
    api_key = _get_api_key()
    if not api_key:
        LOGGER.error("No API key available for embedding")
        return [None] * len(texts)
        
    url = f"{BASE_URL}/{EMBED_MODEL}:embedContent?key={api_key}"
    parts = [{"text": text} for text in texts]
    payload = {
        "content": {"parts": parts}
    }
    
    LOGGER.debug(f"Making batch embedding request for {len(texts)} texts")
    LOGGER.debug(f"First text sample: {texts[0][:100]}...")
    
    for attempt in range(MAX_RETRIES):
        try:
            session = _get_session()
            response = session.post(url, json=payload)
            
            if response.status_code == 429:
                delay = _exponential_backoff(attempt)
                LOGGER.warning(f"Rate limited. Retry {attempt + 1}/{MAX_RETRIES}. Waiting {delay:.1f}s...")
                time.sleep(delay)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            
            
            embeddings = _extract_batch_from_response(data, len(texts))
            
            # Check if we got valid embeddings
            if embeddings and embeddings[0] is not None:
                LOGGER.debug(f"Successfully generated embeddings. First embedding shape: {embeddings[0].shape}")
                return embeddings
            else:
                LOGGER.error("Failed to extract valid embeddings from response")
                return [None] * len(texts)
            
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                LOGGER.error(f"Batch embed API call failed after {MAX_RETRIES} retries: {exc}")
                return [None] * len(texts)
            delay = _exponential_backoff(attempt)
            LOGGER.warning(f"API call failed. Retry {attempt + 1}/{MAX_RETRIES}. Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    return [None] * len(texts)

def _categorise_batch_direct(texts: List[str]) -> List[str]:
    """Categorize a batch of texts using direct API call"""
    api_key = _get_api_key()
    if not api_key:
        return ["unknown"] * len(texts)
        
    url = f"{BASE_URL}/models/{CATEGORISER_MODEL}:generateContent?key={api_key}"
    prompt = (
        f"Categorise these items into one of these categories: "
        f"{', '.join(CATEGORIES.keys())}. Return just the category names, one per line.\n\n"
        f"Items:\n" + "\n".join(f"{i+1}. {text}" for i, text in enumerate(texts))
    )
    
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }]
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            with _categorise_lock:
                session = _get_session()
                response = session.post(url, json=payload)
                
                if response.status_code == 429:
                    delay = _exponential_backoff(attempt)
                    LOGGER.warning(f"Rate limited. Retry {attempt + 1}/{MAX_RETRIES}. Waiting {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                if "candidates" in data and data["candidates"]:
                    text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    categories = []
                    for line in text_response.strip().split("\n"):
                        for cat in CATEGORIES.keys():
                            if cat.lower() in line.lower():
                                categories.append(cat)
                                break
                        else:
                            categories.append("unknown")
                    return categories[:len(texts)]  # Ensure we return exactly len(texts) categories
                    
        except Exception as exc:
            if attempt == MAX_RETRIES - 1:
                LOGGER.error("Batch categorisation API call failed after %d retries: %s", MAX_RETRIES, exc)
                return ["unknown"] * len(texts)
            delay = _exponential_backoff(attempt)
            LOGGER.warning(f"API call failed. Retry {attempt + 1}/{MAX_RETRIES}. Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    return ["unknown"] * len(texts)

def _categorise_direct(text: str) -> str:
    """Categorize a single text using direct API call"""
    return _categorise_batch_direct([text])[0]

# ───────────────────── sync public API ─────────────────────────────
Vector = np.ndarray

def _generate_text_for_embedding(item: Dict[str, Any]) -> str:
    """Generate text for embedding from item fields.
    
    Args:
        item: The item dictionary containing product data
        
    Returns:
        str: Concatenated text for embedding
    """
    # Extract relevant fields
    title = item.get('title', '')
    name = item.get('name', '')
    description = item.get('description', '')
    brand = item.get('brand', '')
    category = item.get('category', '')
    store_name = item.get('store_name', '')
    size = item.get('size', '')
    
    # Build text components
    components = []
    
    # Add title/name (prefer title if available)
    if title:
        components.append(title)
    elif name:
        components.append(name)
        
    # Add brand if available
    if brand:
        components.append(f"Brand: {brand}")
        
    # Add category if available
    if category:
        components.append(f"Category: {category}")
        
    # Add store name if available
    if store_name:
        components.append(f"Store: {store_name}")
        
    # Add size if available
    if size:
        components.append(f"Size: {size}")
        
    # Add description if available
    if description:
        components.append(description)
        
    # Join all components with spaces
    text = " ".join(components)
    
    # Clean up the text
    text = " ".join(text.split())  # Remove extra whitespace
    text = text.strip()
    
    return text

def generate_embeddings_batch(texts: List[str]) -> Tuple[List[Vector], List[str]]:
    """Generate embeddings and categories for a batch of texts"""
    zeros = np.zeros(EMB_DIM, np.float32)
    vecs: List[Optional[Vector]] = [None] * len(texts)
    cats: List[str] = ["unknown"] * len(texts)
    
    # Filter out empty texts
    idx_keep, txt_keep = [], []
    for i, t in enumerate(texts):
        if t and t.strip():
            idx_keep.append(i)
            txt_keep.append(t.strip())
        else:
            LOGGER.warning(f"Empty text at index {i}")
            vecs[i] = zeros
    
    if not txt_keep:
        LOGGER.error("No valid texts to process")
        return [zeros] * len(texts), cats
        
    LOGGER.info(f"Processing {len(txt_keep)} valid texts out of {len(texts)} total")
    
    # Process in smaller batches to avoid rate limits
    for start in range(0, len(txt_keep), MAX_BATCH):
        chunk = txt_keep[start : start + MAX_BATCH]
        idxs = idx_keep[start : start + MAX_BATCH]
        
        LOGGER.debug(f"Processing batch {start//MAX_BATCH + 1} with {len(chunk)} items")
        
        # Get categories for this chunk
        chunk_cats = _categorise_batch_direct(chunk)
        for i, cat in zip(idxs, chunk_cats):
            cats[i] = cat
            
        # Get embeddings for this chunk
        chunk_vecs = _embed_batch_direct(chunk)
        for i, vec in zip(idxs, chunk_vecs):
            vecs[i] = vec if vec is not None else zeros
            
        # Add a small delay between batches to avoid rate limits
        if start + MAX_BATCH < len(txt_keep):
            time.sleep(0.5)
    
    return [v if v is not None else zeros for v in vecs], cats

def generate_embedding(text_or_list: Union[str, List[str], Dict[str, Any], List[Dict[str, Any]]]) -> Union[Tuple[Vector, str], Tuple[List[Vector], List[str]]]:
    """Generate embedding and category for text or list of texts/items
    
    Args:
        text_or_list: Can be:
            - A string
            - A list of strings
            - A dictionary (item)
            - A list of dictionaries (items)
            
    Returns:
        Union[Tuple[Vector, str], Tuple[List[Vector], List[str]]]: 
            For single input: (embedding vector, category)
            For list input: (list of embedding vectors, list of categories)
    """
    # Handle single item dictionary
    if isinstance(text_or_list, dict):
        text = _generate_text_for_embedding(text_or_list)
        if not text:
            return np.zeros(EMB_DIM, np.float32), "unknown"
        vec = _embed_single_direct(text)
        vec = vec if vec is not None else np.zeros(EMB_DIM, np.float32)
        return vec, _categorise_direct(text)
        
    # Handle list of item dictionaries
    if isinstance(text_or_list, list) and text_or_list and isinstance(text_or_list[0], dict):
        texts = [_generate_text_for_embedding(item) for item in text_or_list]
        return generate_embeddings_batch(texts)
        
    # Handle string
    if isinstance(text_or_list, str):
        text = text_or_list.strip()
        if not text:
            return np.zeros(EMB_DIM, np.float32), "unknown"
        vec = _embed_single_direct(text)
        vec = vec if vec is not None else np.zeros(EMB_DIM, np.float32)
        return vec, _categorise_direct(text)
        
    # Handle list of strings
    if isinstance(text_or_list, list):
        return generate_embeddings_batch(text_or_list)
        
    raise TypeError("Input must be str, List[str], Dict[str, Any], or List[Dict[str, Any]]")

# ───────────────────── utilities ─────────────────────────────────

def save_embedding(emb: Union[np.ndarray, List[float]], path: str) -> bool:
    """Save embedding to file"""
    vec = emb.tolist() if isinstance(emb, np.ndarray) else emb
    try:
        temp_path = f"{path}.tmp"
        parent_dir = Path(path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w") as f:
            json.dump(vec, f)
        os.rename(temp_path, path)
        return True
    except Exception as exc:
        LOGGER.error("Failed to save embedding: %s", exc)
        return False

def generate_embedding_deferred(text_or_list: Union[str, List[str]]) -> defer.Deferred:
    """Generate embedding in a separate thread for Twisted"""
    return threads.deferToThread(generate_embedding, text_or_list)

# ───────────────────── async wrapper ─────────────────────────────

class EmbeddingUtils:
    """Async helper for embeddings using direct API calls."""

    def __init__(self, api_key: str):
        self._init_lock = asyncio.Lock()
        self._categorize_locks = {}
        self.api_key = api_key
        self.batch_size = 64
        self.retry_delay = 2  # seconds
        self.max_retries = 3

    async def _create_session(self):
        """Create aiohttp session if it doesn't exist"""
        if not hasattr(self, "_session") or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session"""
        if hasattr(self, "_session") and not self._session.closed:
            await self._session.close()

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Return a single embedding as a plain Python list (or *None*)."""
        if not text.strip():
            return [0.0] * EMB_DIM
        url = f"{BASE_URL}/{EMBED_MODEL}:embedContent?key={self.api_key}"
        payload = {
            "content": {"parts": [{"text": text}]}
        }
        session = await self._create_session()
        for attempt in range(self.max_retries):
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 429:
                        LOGGER.warning(f"Rate limited. Retry {attempt+1}/{self.max_retries}. Waiting {self.retry_delay}s")
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    response.raise_for_status()
                    data = await response.json()
                    vec = _extract_embedding_from_response(data)
                    return vec.tolist() if vec is not None else None
            except Exception as exc:
                LOGGER.error(f"Async embed error (attempt {attempt+1}/{self.max_retries}): {exc}")
                await asyncio.sleep(self.retry_delay)
        return None

    async def batch_embed(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Embed a list of texts asynchronously (chunked to avoid quota)."""
        out: List[Optional[List[float]]] = []
        sem = asyncio.Semaphore(5)
        async def _process_chunk(chunk):
            async with sem:
                url = f"{BASE_URL}/{EMBED_MODEL}:embedContent?key={self.api_key}"
                parts = [{"text": text} for text in chunk]
                payload = {
                    "content": {"parts": parts}
                }
                session = await self._create_session()
                for attempt in range(self.max_retries):
                    try:
                        async with session.post(url, json=payload) as response:
                            if response.status == 429:
                                LOGGER.warning(f"Rate limited. Retry {attempt+1}/{self.max_retries}. Waiting {self.retry_delay}s")
                                await asyncio.sleep(self.retry_delay * (attempt + 1))
                                continue
                            response.raise_for_status()
                            data = await response.json()
                            vecs = _extract_batch_from_response(data, len(chunk))
                            return [v.tolist() if v is not None else None for v in vecs]
                    except Exception as exc:
                        LOGGER.error(f"Async batch embed error (attempt {attempt+1}/{self.max_retries}): {exc}")
                        await asyncio.sleep(self.retry_delay)
                return [None] * len(chunk)
        tasks = []
        for start in range(0, len(texts), self.batch_size):
            chunk = texts[start : start + self.batch_size]
            tasks.append(_process_chunk(chunk))
        results = await asyncio.gather(*tasks)
        for chunk_result in results:
            out.extend(chunk_result)
        return out

    async def categorize_item(self, item: Dict[str, Any]) -> str:
        """Categorise a product-like dict into a coarse category."""
        item_key = hash(frozenset(item.items()))
        if item_key not in self._categorize_locks:
            self._categorize_locks[item_key] = asyncio.Lock()
        async with self._categorize_locks[item_key]:
            text = f"{item.get('name','')} {item.get('description','')} {item.get('brand','')}"
            url = f"{BASE_URL}/models/{CATEGORISER_MODEL}:generateContent?key={self.api_key}"
            prompt = (
                "Categorize this product into one of these categories: "
                "Groceries, Electronics, Clothing, Home & Garden, Sports & Outdoors, "
                "Health & Beauty, Toys & Games, Books & Media, Automotive, Other.\n"
                f"Product: {text}"
            )
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }]
            }
            session = await self._create_session()
            for attempt in range(self.max_retries):
                try:
                    async with session.post(url, json=payload) as response:
                        if response.status == 429:
                            LOGGER.warning(f"Rate limited. Retry {attempt+1}/{self.max_retries}. Waiting {self.retry_delay}s")
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        response.raise_for_status()
                        data = await response.json()
                        if "candidates" in data and data["candidates"]:
                            text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                            for cat in CATEGORIES.keys():
                                if cat.lower() in text_response.lower():
                                    return cat
                        return "unknown"
                except Exception as exc:
                    LOGGER.error(f"Async categorisation error (attempt {attempt+1}/{self.max_retries}): {exc}")
                    await asyncio.sleep(self.retry_delay)
            return "unknown"

# Thread pool executor for parallel operations
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

# ───────────────────────── CLI smoke-test ─────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import concurrent.futures

    print("=== Single ===")
    vec, cat = generate_embedding("{'crawled_at': '2025-05-11T07:50:58.737376', 'image_urls': [], 'metadata': {}, 'is_processed': True, 'processing_status': 'success', 'currency': 'EUR', 'country': 'Austria', 'discount_percentage': None, 'brand': None, 'category': None, 'valid_from': None, 'valid_until': None, 'address': None, 'city': None, 'state': None, 'postal_code': None, 'location': None, 'description': None, 'source': 'penny.at', 'source_id': None, 'product_id': None, 'product_url': 'https://www.penny.at/produkte/lindt-excellence-85-cacao-78116458', 'store_name': 'Penny', 'store_id': None, 'store_url': None, 'price_per_unit': None, 'stock_info': None, 'embedding': None, 'error_message': None, 'source_url': 'https://www.penny.at/angebote', 'url': 'https://www.penny.at/produkte/lindt-excellence-85-cacao-78116458', 'name': 'Lindt Excellence 85% Cacao', 'size': '100 g', 'validity_dates': 'von Mo 12.05.2025bis Mi 14.05.2025', 'title': 'Lindt Excellence 85% Cacao'}")
    print(f"vector len {len(vec)} · category {cat}")

    print("\n=== Batch ===")
    sentences = ["apple", "banana", "", "laptop"]
    vecs, cats = generate_embeddings_batch(sentences)
    for s, v, c in zip(sentences, vecs, cats):
        print(f"{s!r:<8} → {c:<11} len={len(v)}")

    print("\n=== Thread safety test ===")
    def thread_test(item):
        result = generate_embedding(item)
        return result

    # Test multiple threads accessing the API simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(thread_test, item) for item in ["car", "phone", "tv", "book"] * 2]
        for future in concurrent.futures.as_completed(futures):
            try:
                vec, cat = future.result()
                print(f"Thread result: category {cat}, vector length {len(vec)}")
            except Exception as e:
                print(f"Thread error: {e}")

    async def _run_async():
        key = os.getenv("GEMINI_API_KEY") or ""
        helper = EmbeddingUtils(key)
        print("\n=== Async single ===")
        v = await helper.get_embedding("hello world")
        print(len(v) if v else None)
        
        # Test concurrent async operations
        print("\n=== Async concurrency test ===")
        tasks = [helper.get_embedding(f"test item {i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        print(f"Processed {len([r for r in results if r])} items successfully")
        
        # Clean up
        await helper.close()

    asyncio.run(_run_async())