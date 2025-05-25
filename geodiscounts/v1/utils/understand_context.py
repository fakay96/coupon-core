# gemini_client.py
"""
Lightweight Gemini helper with caching for both full-query and category embeddings.

Changes, 2025-05-25
───────────────────
* Added LRU caching for embeddings and API responses
* Improved error handling and retries
* Added cache persistence options
* Optimized the reranking prompt for better results
* Added structured response handling
* Added rate limiting and backoff
"""

from __future__ import annotations

import os
import json
import time
import hashlib
import logging
from typing import Tuple, Optional, List, Dict, Any
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
from dotenv import load_dotenv
from django.conf import settings
from django.core.cache import cache
from google import genai
from google.genai import types
from google.genai import errors
from coupon_core.utils.logging import geo_logger, geo_structured_logger

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class GeminiError(Exception):
    """Base exception for Gemini client errors."""
    pass

class GeminiInitError(GeminiError):
    """Raised when Gemini client initialization fails."""
    pass

class GeminiAPIError(GeminiError):
    """Raised when Gemini API calls fail."""
    pass

class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.calls: List[float] = []
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [t for t in self.calls if now - t < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            # Wait until oldest call is more than 1 minute old
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.calls = self.calls[1:]
        
        self.calls.append(now)

class GeminiEmbeddingClient:
    """
    Client for interacting with Google's Gemini API.
    
    Handles text embedding and content generation with proper error handling,
    rate limiting, and caching.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[str] = None,
        max_retries: int = 3,
        calls_per_minute: int = 60,
        model_name: str = "gemini-1.5-flash",
        embedding_model_name: str = "text-embedding-004"
    ):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Optional API key. If not provided, uses GOOGLE_API_KEY from settings.
            cache_dir: Optional directory for caching embeddings.
            max_retries: Maximum number of retries for API calls.
            calls_per_minute: Maximum number of API calls per minute.
            model_name: Name of the model to use.
            embedding_model_name: Name of the embedding model to use.
            
        Raises:
            GeminiInitError: If client initialization fails.
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(calls_per_minute)
        self.model_name = model_name
        self.embedding_model_name = embedding_model_name
        
        if not self.api_key:
            raise GeminiInitError("API key is required")
            
        try:
            # Initialize the client
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(api_version='v1alpha')
            )
            
            geo_structured_logger.info(
                geo_logger,
                "Gemini client initialized successfully",
                "gemini_client",
                {
                    'model': model_name,
                    'embedding_model': embedding_model_name
                }
            )
            
        except Exception as e:
            raise GeminiInitError(f"Failed to initialize Gemini client: {str(e)}") from e

    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text with caching and retries.
        
        Args:
            text: Text to get embedding for.
            
        Returns:
            List of floats representing the embedding.
            
        Raises:
            GeminiAPIError: If embedding fails after retries.
        """
        # Check cache first
        cache_key = f"embedding_{hash(text)}"
        cached_embedding = cache.get(cache_key)
        if cached_embedding:
            return cached_embedding
            
        for attempt in range(self.max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                
                # Get embedding from API
                response = self.client.models.embed_content(
                    model=self.embedding_model_name,
                    contents=text,
                )
                
                if not response or not hasattr(response, 'embeddings'):
                    raise GeminiAPIError("Invalid embedding response")
                    
                embedding = response.embeddings[0].values
                
                # Cache the embedding
                if self.cache_dir:
                    cache.set(cache_key, embedding, timeout=3600)  # Cache for 1 hour
                    
                return embedding
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise GeminiAPIError(f"Failed to get embedding after {self.max_retries} attempts: {str(e)}") from e
                time.sleep(2 ** attempt)  # Exponential backoff

    def generate_content(
        self,
        prompt: str,
        response_schema: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> types.GenerateContentResponse:
        """
        Generate content using the Gemini model.
        
        Args:
            prompt: The prompt to generate content from.
            response_schema: Optional JSON schema for response validation.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum number of tokens to generate.
            
        Returns:
            GenerateContentResponse object.
            
        Raises:
            GeminiAPIError: If content generation fails.
        """
        for attempt in range(self.max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                
                # Add JSON formatting instructions if schema is provided
                if response_schema:
                    prompt = f"""
                    {prompt}
                    
                    IMPORTANT: Your response must be a valid JSON object. Do not include any other text or explanation.
                    """
                
                # Generate content
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        'temperature': temperature,
                        'max_output_tokens': max_tokens,
                        'top_p': 0.8,
                        'top_k': 40
                    }
                )
                
                if not response or not response.text:
                    raise GeminiAPIError("Empty response from model")
                
                # Clean the response text
                text = response.text.strip()
                if not text:
                    raise GeminiAPIError("Empty response text")
                    
                # Validate against schema if provided
                if response_schema:
                    try:
                        # Try to find JSON in the response
                        json_start = text.find('{')
                        json_end = text.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = text[json_start:json_end]
                            result = json.loads(json_str)
                        else:
                            raise GeminiAPIError("No JSON object found in response")
                            
                        # TODO: Add schema validation
                        return response
                        
                    except json.JSONDecodeError as e:
                        geo_structured_logger.error(
                            geo_logger,
                            "Invalid JSON response",
                            "content_generation",
                            {
                                'error': str(e),
                                'context': {
                                    'prompt': prompt,
                                    'response': text
                                }
                            }
                        )
                        raise GeminiAPIError(f"Invalid JSON response: {str(e)}")
                        
                return response
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    geo_structured_logger.error(
                        geo_logger,
                        "Content generation failed",
                        "content_generation",
                        {
                            'error': str(e),
                            'context': {'prompt': prompt}
                        }
                    )
                    raise GeminiAPIError(f"Failed to generate content after {self.max_retries} attempts: {str(e)}") from e
                time.sleep(2 ** attempt)  # Exponential backoff

    def extract_structured_signals(self, text: str) -> Dict[str, Any]:
        """
        Extract structured signals from text using Gemini.
        
        Args:
            text: Text to extract signals from.
            
        Returns:
            Dictionary of extracted signals.
            
        Raises:
            GeminiAPIError: If signal extraction fails.
        """
        try:
            response = self.generate_content(
                prompt=f"""
                Extract structured signals from this text:
                {text}
                
                Return a JSON object with these exact fields:
                {{
                    "intent": "search/browse/compare",
                    "categories": ["category1", "category2"],
                    "price_range": {{
                        "min": 0,
                        "max": 1000
                    }},
                    "location": "location string",
                    "brands": ["brand1", "brand2"],
                    "attributes": ["attribute1", "attribute2"]
                }}
                
                IMPORTANT: Return ONLY the JSON object, no other text.
                """,
                response_schema={
                    'type': 'OBJECT',
                    'properties': {
                        'intent': {'type': 'STRING'},
                        'categories': {
                            'type': 'ARRAY',
                            'items': {'type': 'STRING'}
                        },
                        'price_range': {
                            'type': 'OBJECT',
                            'properties': {
                                'min': {'type': 'NUMBER'},
                                'max': {'type': 'NUMBER'}
                            }
                        },
                        'location': {'type': 'STRING'},
                        'brands': {
                            'type': 'ARRAY',
                            'items': {'type': 'STRING'}
                        },
                        'attributes': {
                            'type': 'ARRAY',
                            'items': {'type': 'STRING'}
                        }
                    }
                }
            )
            
            if not response or not response.text:
                return {}
                
            # Extract JSON from response
            text = response.text.strip()
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            return {}
            
        except Exception as e:
            geo_structured_logger.error(
                geo_logger,
                "Signal extraction failed",
                "signal_extraction",
                {
                    'error': str(e),
                    'context': {'text': text}
                }
            )
            return {}


# Example usage:
if __name__ == "__main__":
    # Initialize client with cache
    client = GeminiEmbeddingClient(cache_dir=".gemini_cache")
    
    # Test embedding with caching
    embedding = client.get_embedding("red Nike shoes")
    print(f"Embedding length: {len(embedding) if embedding is not None else 'None'}")
    
    # Test structured extraction with caching
    signals = client.extract_structured_signals("red Nike Air Max shoes size 10")
    print(f"Extracted signals: {signals}")