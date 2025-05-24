# discountcrawlers/utils/embedding.py
"""
Google Generative AI helper – *single file, fully working* (SDK ≥ 0.5)
====================================================================

• Generates embeddings via **text‑embedding‑005** (single or batch)
• Optionally maps each text into a coarse domain category
• Pure‑sync implementation — no extra `Client` classes; we just call the
  top‑level helpers that the SDK actually exports (`embed_content`).
• Extra utilities: save vectors as JSON, Twisted‑friendly Deferred wrapper.

For async needs, call `google.generativeai.embed_content_async()` directly.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types
from twisted.internet import defer, threads

load_dotenv()
LOGGER = logging.getLogger(__name__)

# ─────────────────────────── configuration ────────────────────────────
EMBED_MODEL = "models/text-embedding-004"          # 768‑D vectors
CATEGORISER_MODEL = "gemini-1.5-flash"
EMB_DIM = 768
MAX_BATCH = 500

CATEGORIES: Dict[str, str] = {
    "flight": "Travel and flight-related deals",
    "fashion": "Clothing and accessories",
    "furniture": "Home furniture and decor",
    "electronics": "Electronic devices and gadgets",
    "grocery": "Food and grocery items",
}

# ─────────────────────────── SDK one‑time config ──────────────────────

_sdk_init_lock = threading.Lock()
_sdk_initialized = False

def _sdk_ready() -> bool:
    """Initialize the Google Generative AI SDK with the API key.
    
    Returns:
        bool: True if initialization was successful, False otherwise.
    """
    global _sdk_initialized
    
    if _sdk_initialized:
        return True
        
    with _sdk_init_lock:
        if _sdk_initialized:  # Double-check within lock
            return True
            
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            LOGGER.error("GEMINI_API_KEY environment variable not set")
            return False
            
        try:
            genai.configure(api_key=key)
            _sdk_initialized = True
            return True
        except Exception as exc:
            LOGGER.error("Failed to initialize Google Generative AI SDK: %s", exc)
            return False

# ─────────────────────────── response helpers ─────────────────────────

def _vec(obj: Any) -> Optional[np.ndarray]:
    """Convert SDK proto/dict into float32 numpy array.
    
    Args:
        obj: Object containing embedding values
        
    Returns:
        Optional[np.ndarray]: Numpy array of embedding values or None if conversion fails
    """
    try:
        if hasattr(obj, "values"):
            return np.asarray(obj.values, np.float32)
        if isinstance(obj, dict) and "values" in obj:
            return np.asarray(obj["values"], np.float32)
    except Exception as exc:
        LOGGER.error("Bad vector object: %s", exc)
    return None


def _extract_single(resp: Any) -> Optional[np.ndarray]:
    """Extract a single embedding from a response.
    
    Args:
        resp: Response object from the embedding API
        
    Returns:
        Optional[np.ndarray]: Extracted embedding vector or None if extraction fails
    """
    if hasattr(resp, "embedding"):
        return _vec(resp.embedding)
    if hasattr(resp, "embeddings") and resp.embeddings:
        return _vec(resp.embeddings[0])
    if isinstance(resp, dict):
        src = resp.get("embedding") or (resp.get("embeddings") or [None])[0]
        return _vec(src)
    LOGGER.error("Unknown single-embed response shape")
    return None


def _extract_batch(resp: Any, want: int) -> List[Optional[np.ndarray]]:
    """Extract multiple embeddings from a batch response.
    
    Args:
        resp: Response object from the embedding API
        want: Expected number of embeddings
        
    Returns:
        List[Optional[np.ndarray]]: List of extracted embedding vectors, with None for failed extractions
    """
    embeds = None
    if hasattr(resp, "embeddings"):
        embeds = resp.embeddings
    elif isinstance(resp, dict):
        embeds = resp.get("embeddings") or resp.get("embedding")
    if embeds is None:
        LOGGER.error("Embed response lacks list")
        return [None] * want
    out = [_vec(e) for e in embeds]
    out.extend([None] * (want - len(out)))
    return out[:want]

# ─────────────────────────── low‑level embeds ─────────────────────────

def _embed_single(text: str) -> Optional[np.ndarray]:
    """Generate embedding for a single text string.
    
    Args:
        text: Text to embed
        
    Returns:
        Optional[np.ndarray]: Embedding vector or None if embedding fails
    """
    if not _sdk_ready():
        return None
    try:
        resp = genai.embed_content(model=EMBED_MODEL, content=text)
        return _extract_single(resp)
    except Exception as exc:
        LOGGER.error("Single embed failed: %s", exc)
        return None


def _embed_batch(texts: List[str]) -> List[Optional[np.ndarray]]:
    """Generate embeddings for a batch of text strings.
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List[Optional[np.ndarray]]: List of embedding vectors, with None for failed embeddings
    """
    if not _sdk_ready():
        return [None] * len(texts)
    try:
        resp = genai.embed_content(model=EMBED_MODEL, content=texts)
        return _extract_batch(resp, len(texts))
    except Exception as exc:
        LOGGER.error("Batch embed failed: %s", exc)
        return [None] * len(texts)

# ─────────────────────────── categorisation ───────────────────────────

def _categorise(text: str) -> str:
    """Categorize text into one of the predefined categories.
    
    Args:
        text: Text to categorize
        
    Returns:
        str: Category name or "unknown" if categorization fails
    """
    if not _sdk_ready():
        return "unknown"
    prompt = (
        "Categorise this item into one of these categories: "
        + ", ".join(CATEGORIES.keys())
        + ". Return just the category name.\nItem: "
        + text
    )
    try:
        model = genai.GenerativeModel(CATEGORISER_MODEL)
        resp = model.generate_content(prompt, generation_config=types.GenerationConfig(temperature=0.0))
        cat = resp.text.strip().lower()
        return cat if cat in CATEGORIES else "unknown"
    except Exception as exc:
        LOGGER.error("Categorisation failed: %s", exc)
        return "unknown"

# ─────────────────────────── public sync API ─────────────────────────
Vector = np.ndarray

def generate_embeddings_batch(texts: List[str]) -> Tuple[List[Vector], List[str]]:
    """Generate embeddings and categories for a batch of texts.
    
    Args:
        texts: List of text strings to process
        
    Returns:
        Tuple[List[Vector], List[str]]: Tuple containing list of embedding vectors and list of categories
    """
    zeros = np.zeros(EMB_DIM, np.float32)
    vecs: List[Optional[Vector]] = [None] * len(texts)
    cats: List[str] = ["unknown"] * len(texts)

    non_empty_idx, non_empty_txt = [], []
    for i, t in enumerate(texts):
        if t and t.strip():
            non_empty_idx.append(i)
            non_empty_txt.append(t.strip())
            cats[i] = _categorise(t.strip())
        else:
            vecs[i] = zeros

    for start in range(0, len(non_empty_txt), MAX_BATCH):
        chunk = non_empty_txt[start : start + MAX_BATCH]
        idxs = non_empty_idx[start : start + MAX_BATCH]
        results = _embed_batch(chunk)
        for j, v in enumerate(results):
            if j < len(idxs):  # Guard against index out of range
                vecs[idxs[j]] = v if v is not None else zeros

    return [v if v is not None else zeros for v in vecs], cats


def generate_embedding(text_or_list: Union[str, List[str]]) -> Union[Tuple[Vector, str], Tuple[List[Vector], List[str]]]:
    """Generate embedding and category for text or batch of texts.
    
    Args:
        text_or_list: Single text string or list of text strings
        
    Returns:
        Union[Tuple[Vector, str], Tuple[List[Vector], List[str]]]: 
            For single text: (embedding vector, category)
            For list of texts: (list of embedding vectors, list of categories)
            
    Raises:
        TypeError: If input is neither str nor List[str]
    """
    if isinstance(text_or_list, str):
        text = text_or_list.strip()
        if not text:
            return np.zeros(EMB_DIM, np.float32), "unknown"
        vec = _embed_single(text) or np.zeros(EMB_DIM, np.float32)
        return vec, _categorise(text)
    if isinstance(text_or_list, list):
        return generate_embeddings_batch(text_or_list)
    raise TypeError("Input must be str or List[str]")

# ─────────────────────────── misc utilities ──────────────────────────

def save_embedding(emb: Union[np.ndarray, List[float]], path: str) -> bool:
    """Save embedding vector to a JSON file.
    
    Args:
        emb: Embedding vector as numpy array or list of floats
        path: Path to save the JSON file
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    vec = emb.tolist() if isinstance(emb, np.ndarray) else emb
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(vec, f)
        return True
    except Exception as exc:
        LOGGER.error("Failed to save embedding: %s", exc)
        return False


def generate_embedding_deferred(text_or_list: Union[str, List[str]]) -> defer.Deferred:
    """Twisted-friendly wrapper running the sync helper in a thread.
    
    Args:
        text_or_list: Single text string or list of text strings
        
    Returns:
        defer.Deferred: Deferred that will fire with the result of generate_embedding
    """
    return threads.deferToThread(generate_embedding, text_or_list)

# ────────────────────────────── smoke test ───────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Single ===")
    v, c = generate_embedding("The quick brown fox jumps over the lazy dog")
    print(f"Vector length: {len(v)}, Category: {c}")

    print("\n=== Batch ===")
    test_texts = ["{'crawled_at': '2025-05-10T20:50:19.957738', 'image_urls': [], 'metadata': {}, 'is_processed': True, 'processing_status': 'success', 'currency': 'EUR', 'country': 'Austria', 'discount_percentage': None, 'brand': None, 'category': None, 'valid_from': None, 'valid_until': None, 'address': None, 'city': None, 'state': None, 'postal_code': None, 'location': None, 'description': None, 'source': 'penny.at', 'source_id': None, 'product_id': None, 'product_url': 'https://www.penny.at/produkte/fisolen-breit-78117657', 'store_name': 'Penny', 'store_id': None, 'store_url': None, 'price_per_unit': None, 'stock_info': None, 'embedding': None, 'error_message': None, 'source_url': 'https://www.penny.at/angebote', 'url': 'https://www.penny.at/produkte/fisolen-breit-78117657', 'name': 'Fisolen Breit', 'size': '500 g', 'validity_dates': 'von Mo 12.05.2025bis Mi 14.05.2025', 'title': 'Fisolen Breit'}", "banana", "", "laptop"]
    vecs, cats = generate_embeddings_batch(test_texts)
    for t, v, c in zip(test_texts, vecs, cats):
        print(f"{t!r:<8} → {c:<11} vec_len={len(v) if v is not None else 'None'}")