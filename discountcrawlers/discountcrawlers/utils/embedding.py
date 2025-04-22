"""discountcrawlers.utils.embedding

Utility functions for generating embeddings using Google's Generative AI API.
Integrated with Twisted's deferred model for asynchronous operations (though the current implementation is synchronous blocking).

Key features
------------
* Safe configuration – no API key baked into the source.
* One public function, ``generate_embedding``,
  accepts **either** a single string **or** a list of strings and returns
  the corresponding embedding(s).
* Robust batching with index‑safe round‑tripping (when batching is used).
* Item categorization into predefined categories.
"""

from __future__ import annotations

import os
import json
import logging
from typing import List, Optional, Union, Dict, Any, Tuple

import numpy as np
from google import genai
from dotenv import load_dotenv
from twisted.internet import defer, threads

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------

load_dotenv()
LOGGER = logging.getLogger(__name__)

# Define the model name and expected dimension
# Model list: https://ai.google.dev/models/gemini
# Embedding models: https://ai.google.dev/docs/embeddings#available_models
EMBEDDING_MODEL_NAME = "models/embedding-001"
EMBEDDING_DIMENSION = 768  # Dimension for embedding-001
# Max batch size for the embedding model (consult documentation if needed, 100 is often safe)
MAX_BATCH_SIZE = 100

# Define available categories
CATEGORIES = {
    "flight": "Travel and flight-related deals",
    "fashion": "Clothing, accessories, and fashion items",
    "furniture": "Home furniture and decor",
    "electronics": "Electronic devices and gadgets",
    "grocery": "Food and grocery items"
}

_genai_initialized = False

def initialize_client() -> bool:
    """Initialize the Google Generative AI client with API key.

    Returns:
        bool: True if initialization was successful or already done, False otherwise.
    """
    global _genai_initialized
    if _genai_initialized:
        return True

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        LOGGER.error("GEMINI_API_KEY environment variable not set")
        return False
    try:
        genai.Client(api_key=api_key)
        LOGGER.info("Google Generative AI client initialized successfully.")
        _genai_initialized = True
        return True
    except Exception as e:
        LOGGER.exception(f"Failed to initialize Google Generative AI client: {e}")
        return False

# ---------------------------------------------------------------------------
# Core embedding functions
# ---------------------------------------------------------------------------

def _generate_single_embedding(text: str) -> Optional[np.ndarray]:
    """Generate an embedding for a single non-empty text string using the API."""
    try:
        # Use the top-level genai.embed_content function
        result = genai.embed_content(
            model=EMBEDDING_MODEL_NAME,
            content=text,
            task_type="RETRIEVAL_DOCUMENT"  # Or choose appropriate task type
            # Other task types: RETRIEVAL_QUERY, SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING
        )
        # The result is a dictionary containing the embedding list
        if 'embedding' in result and result['embedding']:
            return np.array(result['embedding'], dtype=np.float32)
        else:
            LOGGER.error("No embedding returned from model for text: %s...", text[:50])
            return None
    except Exception as e:
        LOGGER.error(f"Failed to generate embedding for text '{text[:50]}...': {str(e)}")
        return None

def _categorize_item(text: str) -> str:
    """Categorize an item based on its description using Gemini API.
    
    Args:
        text: The item description to categorize.
        
    Returns:
        str: The category name (one of the keys in CATEGORIES) or 'unknown' if categorization fails.
    """
    if not initialize_client():
        LOGGER.error("Cannot categorize item, client not initialized.")
        return "unknown"

    try:
        # Create a prompt for categorization
        prompt = f"""Categorize the following item into one of these categories: {', '.join(CATEGORIES.keys())}.
        Return ONLY the category name, nothing else.
        
        Item description: {text}
        """
        
        # Use Gemini for categorization
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Extract the category from the response
        category = response.text.strip().lower()
        
        # Validate the category
        if category in CATEGORIES:
            return category
        else:
            LOGGER.warning(f"Invalid category returned: {category}")
            return "unknown"
            
    except Exception as e:
        LOGGER.error(f"Failed to categorize item: {str(e)}")
        return "unknown"

def _generate_batch_embeddings(texts: List[str]) -> List[Optional[np.ndarray]]:
    """Generate embeddings for a batch of non-empty text strings using the API."""
    if not texts:
        return []
    try:
        # Use the top-level genai.embed_content function for batching
        result = genai.embed_content(
            model=EMBEDDING_MODEL_NAME,
            content=texts,
            task_type="RETRIEVAL_DOCUMENT"  # Use consistent task type for batch
        )
        # The result contains a list of embeddings under the 'embedding' key
        if 'embedding' in result and isinstance(result['embedding'], list) and len(result['embedding']) == len(texts):
            # Convert each list embedding to a numpy array
            return [np.array(emb, dtype=np.float32) if emb else None for emb in result['embedding']]
        else:
            LOGGER.error(f"Mismatched result count or missing embedding key in batch response. Expected {len(texts)} embeddings.")
            return [None] * len(texts)  # Return None for all if batch failed
    except Exception as e:
        LOGGER.error(f"Failed to generate embeddings batch (first text: '{texts[0][:50]}...'): {str(e)}")
        return [None] * len(texts)  # Return None for all if batch failed

def generate_embeddings_batch(texts: List[str]) -> Tuple[List[np.ndarray], List[str]]:
    """Generate embeddings and categories for a batch of texts.

    Args:
        texts: List of texts to generate embeddings for.

    Returns:
        Tuple containing:
        - List of numpy arrays containing embedding vectors
        - List of category names for each text
    """
    if not initialize_client():
        LOGGER.error("Cannot generate embeddings, client not initialized.")
        return (
            [np.zeros(EMBEDDING_DIMENSION, dtype=np.float32) for _ in texts],
            ["unknown"] * len(texts)
        )

    if not texts:
        return [], []

    results: List[Optional[np.ndarray]] = [None] * len(texts)
    categories: List[str] = ["unknown"] * len(texts)
    non_empty_indices: List[int] = []
    non_empty_texts: List[str] = []

    # Identify non-empty texts and their original indices
    for i, text in enumerate(texts):
        if text and text.strip():
            non_empty_indices.append(i)
            non_empty_texts.append(text.strip())  # Use stripped text
            # Categorize the item
            categories[i] = _categorize_item(text.strip())
        else:
            LOGGER.warning(f"Empty text provided at index {i} in batch, using zero vector.")
            results[i] = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

    # Process non-empty texts in batches respecting the API limit
    for i in range(0, len(non_empty_texts), MAX_BATCH_SIZE):
        batch_texts = non_empty_texts[i:i + MAX_BATCH_SIZE]
        batch_indices = non_empty_indices[i:i + MAX_BATCH_SIZE]

        if not batch_texts:  # Should not happen with the range logic, but safe check
            continue

        LOGGER.debug(f"Generating embeddings for batch of {len(batch_texts)} texts (starting index {batch_indices[0]})")
        batch_embeddings = _generate_batch_embeddings(batch_texts)

        # Place successful embeddings back into the results list, use zeros for failures
        for j, embedding in enumerate(batch_embeddings):
            original_index = batch_indices[j]
            if embedding is not None and embedding.shape == (EMBEDDING_DIMENSION,):
                results[original_index] = embedding
            else:
                LOGGER.warning(f"Failed to generate embedding for text at original index {original_index}, using zero vector.")
                results[original_index] = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

    # Final check: ensure all slots in results are filled (they should be by now)
    final_embeddings = []
    for i, res in enumerate(results):
        if res is None:
            LOGGER.error(f"Result at index {i} remained None unexpectedly. Using zero vector.")
            final_embeddings.append(np.zeros(EMBEDDING_DIMENSION, dtype=np.float32))
        else:
            final_embeddings.append(res)

    return final_embeddings, categories

def generate_embedding(text_or_texts: Union[str, List[str]]) -> Union[Tuple[np.ndarray, str], Tuple[List[np.ndarray], List[str]]]:
    """Generate embedding(s) and category/categories for a single text or a list of texts.

    Args:
        text_or_texts: Either a single string or a list of strings.

    Returns:
        For single string input:
        - Tuple of (embedding, category)
        For list input:
        - Tuple of (list of embeddings, list of categories)
    """
    if isinstance(text_or_texts, str):
        # Handle single string case
        if not initialize_client():
            LOGGER.error("Cannot generate embedding, client not initialized.")
            return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32), "unknown"

        text = text_or_texts.strip()
        if not text:
            LOGGER.warning("Empty text provided for embedding, using zero vector.")
            return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32), "unknown"

        embedding = _generate_single_embedding(text)
        category = _categorize_item(text)
        
        if embedding is None:
            LOGGER.warning("Failed to generate embedding for single text, using zero vector.")
            return np.zeros(EMBEDDING_DIMENSION, dtype=np.float32), category
        return embedding, category
    elif isinstance(text_or_texts, list):
        # Handle list of strings case using the batch function
        return generate_embeddings_batch(text_or_texts)
    else:
        raise TypeError("Input must be a string or a list of strings")

def save_embedding(embedding: Union[np.ndarray, List[float]], path: str) -> bool:
    """Save an embedding vector (as list) to a JSON file.

    Args:
        embedding: The embedding vector (NumPy array or list) to save.
        path: Path to save the JSON file.

    Returns:
        True if save was successful, False otherwise.
    """
    # Convert numpy array to list for JSON serialization
    if isinstance(embedding, np.ndarray):
        embedding_list = embedding.tolist()
    elif isinstance(embedding, list):
        embedding_list = embedding
    else:
        LOGGER.error("Invalid type for embedding, must be numpy array or list.")
        return False

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)  # Ensure directory exists
        with open(path, 'w') as f:
            json.dump(embedding_list, f)
        LOGGER.debug(f"Embedding saved successfully to {path}")
        return True
    except Exception as e:
        LOGGER.error(f"Failed to save embedding to {path}: {str(e)}")
        return False

# --- Twisted Integration (Example - requires running in Twisted reactor) ---
def generate_embedding_deferred(text_or_texts: Union[str, List[str]]) -> defer.Deferred:
    """Generate embedding(s) asynchronously using Twisted threads.

    Args:
        text_or_texts: Either a single string or a list of strings.

    Returns:
        A Twisted Deferred that will fire with the embedding(s) (np.ndarray or list)
        or errback with an Exception.
    """
    # Run the synchronous generate_embedding function in a thread
    d = threads.deferToThread(generate_embedding, text_or_texts)
    return d

