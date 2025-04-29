"""
discountcrawlers.utils.embedding
================================

High-level helper for **Google Generative AI (Gemini)** embeddings
plus a lightweight text-to-category mapping.

Key points
----------
*   Reads the API key from the **GEMINI_API_KEY** environment variable
    (no secrets in the repo).
*   Supports **single text** or **batch** input with the public functions
    `generate_embedding()` and `generate_embeddings_batch()`.
*   Uses the high-throughput **text-embedding-004** model
    (≈ 500 items per call).
*   Adds an optional “best-effort” categorisation step with *gemini-1.5-flash*.
*   Provides a Twisted-friendly wrapper `generate_embedding_deferred()`.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import numpy as np
from dotenv import load_dotenv

# Import the new SDK
from google import generativeai as genai
from google.generativeai import types
from twisted.internet import defer, threads

load_dotenv()
LOGGER = logging.getLogger(__name__)

# ─────────────────────────── configuration ────────────────────────────

EMBEDDING_MODEL_NAME: str = "models/text-embedding-005"  # Correct model name
EMBEDDING_DIMENSION: int = 768
MAX_BATCH_SIZE: int = 500  # limit for text-embedding-004

CATEGORIES: dict[str, str] = {
    "flight":      "Travel and flight-related deals",
    "fashion":     "Clothing and accessories",
    "furniture":   "Home furniture and decor",
    "electronics": "Electronic devices and gadgets",
    "grocery":     "Food and grocery items",
}

_genai_client: Optional[genai.GenerativeModel] = None

# ───────────────────── initialisation helper ──────────────────────

def _init_genai() -> bool:
    """
    Configure the Google Generative AI client once per process.

    Returns
    -------
    bool
        *True* when the client is ready; *False* on failure.
    """
    global _genai_client
    if _genai_client is not None:
        return True

    api_key: str | None = os.getenv("GEMINI_API_KEY")
    if not api_key:
        LOGGER.error("GEMINI_API_KEY environment variable not set")
        return False

    try:
        genai.configure(api_key=api_key)  # configure API key
        _genai_client = genai.GenerativeModel('gemini-1.5-flash')
        LOGGER.info("Google Generative AI client initialised")
        return True
    except Exception as exc:
        LOGGER.exception("Failed to initialise Gemini client: %s", exc)
        return False

# ────────────────────────── low-level calls ──────────────────────────

def _embed_single(text: str) -> Optional[np.ndarray]:
    """Return a vector for *text* or *None* on failure."""
    if not _init_genai():
        return None
    try:
        model = genai.GenerativeModel(EMBEDDING_MODEL_NAME)
        response = model.embed_content(content=text)
        return np.asarray(response.embedding.value, dtype=np.float32)
    except Exception as exc:
        LOGGER.error("Embedding failed for %.50s… : %s", text, exc)
    return None


def _embed_batch(texts: List[str]) -> List[Optional[np.ndarray]]:
    """Embed up to `MAX_BATCH_SIZE` texts in one API call."""
    if not texts:
        return []
    if not _init_genai():
        return [None] * len(texts)
    try:
        model = genai.GenerativeModel(EMBEDDING_MODEL_NAME)
        response = model.embed_content(content=texts)
        return [np.asarray(embedding.value, dtype=np.float32) for embedding in response.embeddings]
    except Exception as exc:
        LOGGER.error("Batch embedding failed: %s", exc)
    return [None] * len(texts)


def _categorise(text: str) -> str:
    """
    Return one of the keys in ``CATEGORIES`` or ``'unknown'``.
    The prompt is intentionally strict: we expect exactly a category name back.
    """
    if not _init_genai():
        return "unknown"

    prompt = (
        "Categorise this item into one of these categories: "
        + ", ".join(CATEGORIES.keys())
        + ". Return just the category name.\nItem: "
        + text
    )
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        cat = response.text.strip().lower()
        return cat if cat in CATEGORIES else "unknown"
    except Exception as exc:
        LOGGER.error("Categorisation failed: %s", exc)
        return "unknown"

# ─────────────────────── public batch function ───────────────────────

def generate_embeddings_batch(
    texts: List[str],
) -> Tuple[List[np.ndarray], List[str]]:
    """
    Embed and categorise a list of strings.

    Returns
    -------
    Tuple[List[np.ndarray], List[str]]
        *embedding_vectors*, *categories*
    """
    if not _init_genai():
        zeros = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        return [zeros] * len(texts), ["unknown"] * len(texts)

    vectors: List[Optional[np.ndarray]] = [None] * len(texts)
    categories: List[str] = ["unknown"] * len(texts)

    non_empty_idx: List[int] = []
    non_empty_txt: List[str] = []

    for i, t in enumerate(texts):
        if t and t.strip():
            non_empty_idx.append(i)
            non_empty_txt.append(t.strip())
            categories[i] = _categorise(t.strip())
        else:
            vectors[i] = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

    for i in range(0, len(non_empty_txt), MAX_BATCH_SIZE):
        batch = non_empty_txt[i : i + MAX_BATCH_SIZE]
        idxs = non_empty_idx[i : i + MAX_BATCH_SIZE]
        vecs = _embed_batch(batch)
        for j, v in enumerate(vecs):
            vectors[idxs[j]] = (
                v if v is not None
                else np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
            )

    return [v for v in vectors], categories

# ────────────────────── public single / mixed API ─────────────────────

def generate_embedding(
    text_or_list: Union[str, List[str]]
) -> Union[Tuple[np.ndarray, str], Tuple[List[np.ndarray], List[str]]]:
    """
    Embed *one* string or a *list* of strings.

    * **str →**  (*vector*, *category*)
    * **list →** (*vectors*, *categories*)
    """
    if isinstance(text_or_list, str):
        if not _init_genai():
            return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32), "unknown"

        text = text_or_list.strip()
        if not text:
            return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32), "unknown"

        vec = _embed_single(text) or np.zeros(
            EMBEDDING_DIMENSION, dtype=np.float32
        )
        cat = _categorise(text)
        return vec, cat

    if isinstance(text_or_list, list):
        return generate_embeddings_batch(text_or_list)

    raise TypeError("Input must be str or List[str]")

# ─────────────────────────── utilities ───────────────────────────────

def save_embedding(emb: Union[np.ndarray, List[float]], path: str) -> bool:
    """
    Write *emb* to *path* as JSON. Accepts numpy arrays or plain lists.

    Returns
    -------
    bool
        *True* on success, *False* on failure.
    """
    vec: List[float]
    if isinstance(emb, np.ndarray):
        vec = emb.tolist()
    elif isinstance(emb, list):
        vec = emb
    else:
        LOGGER.error("Embedding must be ndarray or list, not %s", type(emb))
        return False

    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(vec))
        return True
    except Exception as exc:
        LOGGER.error("Failed to save embedding: %s", exc)
        return False

# ───────────────────── Twisted-friendly wrapper ──────────────────────

def generate_embedding_deferred(
    text_or_list: Union[str, List[str]]
) -> defer.Deferred:
    """
    Run `generate_embedding` in a thread and return a Deferred.

    Suitable for use inside a Twisted reactor.
    """
    return threads.deferToThread(generate_embedding, text_or_list)
