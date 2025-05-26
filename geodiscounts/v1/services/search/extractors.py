"""
Extractors for categories and preferences using embeddings.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Union
from django.db.models import Q
from django.utils import timezone

from geodiscounts.models import Category, Retailer
from geodiscounts.v1.utils.understand_context import GeminiEmbeddingClient

logger = logging.getLogger(__name__)

class EmbeddingBasedCategoryService:
    """Service for category extraction and matching using embeddings."""
    
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client
        self._initialize_categories()
    
    def _initialize_categories(self):
        """Initialize category embeddings."""
        try:
            # Get all categories
            categories = Category.objects.using('geodiscounts_db').all()
            
            # Store category embeddings
            self.category_embeddings = {}
            for category in categories:
                if category.embedding:
                    self.category_embeddings[category.name] = category.embedding
            
            logger.info(
                "Initialized category embeddings",
                extra={
                    'category_count': len(self.category_embeddings)
                }
            )
            
        except Exception as e:
            logger.error(
                "Error initializing category embeddings",
                extra={
                    'error': str(e)
                }
            )
            self.category_embeddings = {}
    
    def extract_category(self, text: str) -> Optional[str]:
        """Extract category from text using embeddings."""
        try:
            # Get text embedding
            text_embedding = self.gemini.get_embedding(text)
            
            # Find best matching category
            best_category = None
            best_similarity = 0.7  # Minimum similarity threshold
            
            for category_name, category_embedding in self.category_embeddings.items():
                similarity = self.gemini.calculate_similarity(
                    text_embedding,
                    category_embedding
                )
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_category = category_name
            
            if best_category:
                logger.info(
                    "Extracted category",
                    extra={
                        'text': text,
                        'category': best_category,
                        'similarity': best_similarity
                    }
                )
            
            return best_category
            
        except Exception as e:
            logger.error(
                "Error extracting category",
                extra={
                    'error': str(e),
                    'text': text
                }
            )
            return None
    
    def get_similar_categories(self, category: str, limit: int = 5) -> List[str]:
        """Get similar categories based on embeddings."""
        try:
            if category not in self.category_embeddings:
                return []
            
            category_embedding = self.category_embeddings[category]
            
            # Calculate similarities
            similarities = []
            for other_category, other_embedding in self.category_embeddings.items():
                if other_category != category:
                    similarity = self.gemini.calculate_similarity(
                        category_embedding,
                        other_embedding
                    )
                    similarities.append((other_category, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return [cat for cat, _ in similarities[:limit]]
            
        except Exception as e:
            logger.error(
                "Error getting similar categories",
                extra={
                    'error': str(e),
                    'category': category
                }
            )
            return []

class EmbeddingBasedPreferenceExtractor:
    """Extract user preferences using embeddings."""
    
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        self.gemini = gemini_client
        self._initialize_retailers()
    
    def _initialize_retailers(self):
        """Initialize retailer data for matching."""
        try:
            # Get all retailers with a single optimized query
            retailers = Retailer.objects.using('geodiscounts_db').only(
                'name'
            ).order_by('name')
            
            # Store retailer names and aliases for text matching
            self.retailer_names = set()
            self.retailer_aliases = {}  # Map aliases to canonical names
            
            for retailer in retailers:
                # Store canonical name
                self.retailer_names.add(retailer.name.lower())
                
                # Generate common aliases
                name_parts = retailer.name.lower().split()
                if len(name_parts) > 1:
                    # Add first word as alias
                    self.retailer_aliases[name_parts[0]] = retailer.name
                    # Add last word as alias if different
                    if name_parts[-1] != name_parts[0]:
                        self.retailer_aliases[name_parts[-1]] = retailer.name
            
            logger.info(
                "Initialized retailer data",
                extra={
                    'retailer_count': len(self.retailer_names),
                    'alias_count': len(self.retailer_aliases)
                }
            )
            
        except Exception as e:
            logger.error(
                "Error initializing retailer data",
                extra={
                    'error': str(e)
                }
            )
            self.retailer_names = set()
            self.retailer_aliases = {}
    
    def extract_preferences(self, text: str) -> Dict[str, Any]:
        """Extract user preferences from text."""
        try:
            # Get text embedding
            text_embedding = self.gemini.get_embedding(text)
            
            # Extract brand preferences
            brand_preferences = self._extract_brand_preferences(text_embedding)
            
            # Extract price preferences
            price_preferences = self._extract_price_preferences(text)
            
            # Extract location preferences
            location_preferences = self._extract_location_preferences(text)
            
            preferences = {
                'brand_preferences': brand_preferences,
                'price_preferences': price_preferences,
                'location_preferences': location_preferences
            }
            
            logger.info(
                "Extracted preferences",
                extra={
                    'text': text,
                    'preferences': preferences
                }
            )
            
            return preferences
            
        except Exception as e:
            logger.error(
                "Error extracting preferences",
                extra={
                    'error': str(e),
                    'text': text
                }
            )
            return {
                'brand_preferences': [],
                'price_preferences': None,
                'location_preferences': None
            }
    
    def _extract_brand_preferences(self, text_embedding: List[float]) -> List[str]:
        """Extract brand preferences using text matching."""
        try:
            preferences = set()
            text_lower = text.lower()
            
            # First try exact matches
            for retailer_name in self.retailer_names:
                if retailer_name in text_lower:
                    preferences.add(retailer_name)
            
            # Then try alias matches
            for alias, canonical_name in self.retailer_aliases.items():
                if alias in text_lower:
                    preferences.add(canonical_name)
            
            # If no matches found, try partial matches
            if not preferences:
                for retailer_name in self.retailer_names:
                    # Check if any word in the retailer name appears in the text
                    retailer_words = retailer_name.split()
                    if any(word in text_lower for word in retailer_words):
                        preferences.add(retailer_name)
            
            return list(preferences)
            
        except Exception as e:
            logger.error(
                "Error extracting brand preferences",
                extra={
                    'error': str(e)
                }
            )
            return []
    
    def _extract_price_preferences(self, text: str) -> Optional[Dict[str, float]]:
        """Extract price preferences from text."""
        try:
            # Use Gemini to extract price information
            prompt = f"""Extract price preferences from the following text. Return a JSON object with min_price and max_price in EUR.
            If no specific prices are mentioned, return null.
            Text: {text}"""
            
            response = self.gemini.generate_content(prompt)
            try:
                price_data = response.json()
                if price_data and isinstance(price_data, dict):
                    return {
                        'min_price': float(price_data.get('min_price', 0)),
                        'max_price': float(price_data.get('max_price', float('inf')))
                    }
            except (ValueError, TypeError):
                pass
            
            # Fallback to regex-based extraction
            import re
            price_pattern = r'(\d+(?:\.\d+)?)\s*(?:€|EUR|euro)'
            prices = [float(p) for p in re.findall(price_pattern, text)]
            
            if prices:
                return {
                    'min_price': min(prices),
                    'max_price': max(prices)
                }
            
            return None
            
        except Exception as e:
            logger.error(
                "Error extracting price preferences",
                extra={
                    'error': str(e),
                    'text': text
                }
            )
            return None
    
    def _extract_location_preferences(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract location preferences from text."""
        try:
            # Use Gemini to extract location information
            prompt = f"""Extract location preferences from the following text. Return a JSON object with:
            - city: city name if mentioned
            - radius: search radius in meters if mentioned
            - coordinates: lat/lng if mentioned
            If no location is mentioned, return null.
            Text: {text}"""
            
            response = self.gemini.generate_content(prompt)
            try:
                location_data = response.json()
                if location_data and isinstance(location_data, dict):
                    return {
                        'city': location_data.get('city'),
                        'radius': float(location_data.get('radius', 5000)),  # Default 5km
                        'coordinates': location_data.get('coordinates')
                    }
            except (ValueError, TypeError):
                pass
            
            # Fallback to basic location detection
            location_keywords = ['near me', 'around here', 'local', 'nearby']
            if any(keyword in text.lower() for keyword in location_keywords):
                return {
                    'radius': 5000,  # Default 5km radius
                    'use_current_location': True
                }
            
            return None
            
        except Exception as e:
            logger.error(
                "Error extracting location preferences",
                extra={
                    'error': str(e),
                    'text': text
                }
            )
            return None

class EnhancedProductExtractor:
    """Enhanced product extraction and matching using embeddings."""
    
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        """Initialize the extractor with Gemini client."""
        self.gemini = gemini_client
    
    def extract_product_signals(self, text: str) -> Dict[str, Any]:
        """Extract product-related signals from text.
        
        Args:
            text: The input text to analyze.
            
        Returns:
            Dictionary containing extracted signals like product name, brand,
            attributes, and price range.
        """
        try:
            # Get text embedding
            text_embedding = self.gemini.get_embedding(text)
            
            # Extract structured information
            signals = {
                'product_name': self._extract_product_name(text),
                'brand': self._extract_brand(text),
                'attributes': self._extract_attributes(text),
                'price_range': self._extract_price_range(text),
                'category': self._extract_category(text)
            }
            
            logger.info(
                "Extracted product signals",
                extra={
                    'text': text,
                    'signals': signals
                }
            )
            
            return signals
            
        except Exception as e:
            logger.error(
                "Error extracting product signals",
                extra={
                    'error': str(e),
                    'text': text
                }
            )
            return {}
    
    def _extract_product_name(self, text: str) -> Optional[str]:
        """Extract product name from text."""
        try:
            # Use Gemini to extract product name
            response = self.gemini.generate_content(
                f"Extract the main product name from this text: {text}"
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error extracting product name: {str(e)}")
            return None
    
    def _extract_brand(self, text: str) -> Optional[str]:
        """Extract brand name from text."""
        try:
            # Use Gemini to extract brand
            response = self.gemini.generate_content(
                f"Extract the brand name from this text: {text}"
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error extracting brand: {str(e)}")
            return None
    
    def _extract_attributes(self, text: str) -> List[str]:
        """Extract product attributes from text."""
        try:
            # Use Gemini to extract attributes
            response = self.gemini.generate_content(
                f"Extract product attributes from this text: {text}"
            )
            return [attr.strip() for attr in response.text.split(',')]
        except Exception as e:
            logger.error(f"Error extracting attributes: {str(e)}")
            return []
    
    def _extract_price_range(self, text: str) -> Optional[Dict[str, float]]:
        """Extract price range from text."""
        try:
            # Use Gemini to extract price range
            response = self.gemini.generate_content(
                f"Extract price range from this text in format min,max: {text}"
            )
            if ',' in response.text:
                min_price, max_price = map(float, response.text.split(','))
                return {'min': min_price, 'max': max_price}
            return None
        except Exception as e:
            logger.error(f"Error extracting price range: {str(e)}")
            return None
    
    def _extract_category(self, text: str) -> Optional[str]:
        """Extract category from text."""
        try:
            # Use Gemini to extract category
            response = self.gemini.generate_content(
                f"Extract the product category from this text: {text}"
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error extracting category: {str(e)}")
            return None

class MultilingualMatcher:
    """Multilingual text matching and translation support."""
    
    def __init__(self, gemini_client: GeminiEmbeddingClient):
        """Initialize the matcher with Gemini client."""
        self.gemini = gemini_client
        self.supported_languages = ['en', 'de']  # Add more languages as needed
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the input text.
        
        Args:
            text: The input text to analyze.
            
        Returns:
            Language code (e.g., 'en', 'de').
        """
        try:
            # Use Gemini to detect language
            response = self.gemini.generate_content(
                f"Detect the language of this text and return only the ISO code (en/de): {text}"
            )
            lang = response.text.strip().lower()
            return lang if lang in self.supported_languages else 'en'
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return 'en'  # Default to English
    
    def translate_text(self, text: str, target_lang: str = 'en') -> str:
        """Translate text to target language.
        
        Args:
            text: The text to translate.
            target_lang: Target language code.
            
        Returns:
            Translated text.
        """
        try:
            if target_lang not in self.supported_languages:
                return text
                
            # Use Gemini to translate
            response = self.gemini.generate_content(
                f"Translate this text to {target_lang}: {text}"
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            return text
    
    def match_texts(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts, handling different languages.
        
        Args:
            text1: First text to compare.
            text2: Second text to compare.
            
        Returns:
            Similarity score between 0 and 1.
        """
        try:
            # Get embeddings for both texts
            embedding1 = self.gemini.get_embedding(text1)
            embedding2 = self.gemini.get_embedding(text2)
            
            # Calculate similarity
            similarity = self.gemini.calculate_similarity(embedding1, embedding2)
            
            logger.info(
                "Calculated text similarity",
                extra={
                    'text1': text1,
                    'text2': text2,
                    'similarity': similarity
                }
            )
            
            return similarity
            
        except Exception as e:
            logger.error(
                "Error matching texts",
                extra={
                    'error': str(e),
                    'text1': text1,
                    'text2': text2
                }
            )
            return 0.0
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching.
        
        Args:
            text: Text to normalize.
            
        Returns:
            Normalized text.
        """
        try:
            # Use Gemini to normalize text
            response = self.gemini.generate_content(
                f"Normalize this text for matching (remove special chars, lowercase): {text}"
            )
            return response.text.strip().lower()
        except Exception as e:
            logger.error(f"Error normalizing text: {str(e)}")
            return text.lower() 